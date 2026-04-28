from typing import Annotated

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from pydantic import EmailStr
from shepherd_core.data_models.base.timezone import local_now

from shepherd_server.api_experiments.models import ExperimentStats
from shepherd_server.api_experiments.models import WebExperiment

from .models import PasswordStr
from .models import User
from .models import UserOut
from .models import UserQuota
from .models import UserRegistration
from .models import UserRole
from .models import UserUpdate
from .utils_mail import get_mail_engine
from .utils_misc import active_admin_user
from .utils_misc import active_user
from .utils_misc import calculate_hash
from .utils_misc import calculate_password_hash
from .utils_misc import current_user

router = APIRouter(prefix="/accounts", tags=["Accounts"])


# ###############################################################
# Own Data Access
# ###############################################################


@router.get("")
async def user_info(user: Annotated[User, Depends(current_user)]) -> UserOut:
    """Get info of current user (even deactivated & unconfirmed)."""
    user.storage_available = user.quota_storage - await WebExperiment.get_storage(user)
    await user.save_changes()
    return user


@router.patch("")
async def update_user(update: UserUpdate, user: Annotated[User, Depends(active_user)]) -> UserOut:
    """Update allowed user fields."""
    fields = update.model_dump(exclude_unset=True)
    new_email = fields.pop("email", None)
    if isinstance(new_email, str) and new_email != user.email:
        if await User.by_email(new_email) is not None:
            raise HTTPException(406, "Email already exists")
        raise HTTPException(406, "Changing email currently not supported")
        # await user.update_email(new_email)
    user = user.model_copy(update=fields)
    await user.save()
    return user


@router.delete("")
async def delete_user(
    user: Annotated[User, Depends(current_user)],
) -> Response:
    """Delete current user (even deactivated & unconfirmed) and its experiments & content."""
    xp_states = await WebExperiment.get_all_states(user)
    for xp_id in xp_states:
        xp = await WebExperiment.get_by_id(xp_id)
        if xp is None:
            raise HTTPException(
                406, "Unexpected error while deleting experiments that do not exist"
            )
        await ExperimentStats.update_with(xp, to_be_deleted=True)
        await xp.delete_content()
        await xp.delete()
    await user.delete()
    # TODO: inform user about it
    return Response(status_code=204)


# ###############################################################
# Quota
# ###############################################################


@router.patch("/quota", dependencies=[Depends(active_admin_user)])
async def update_quota(
    email: Annotated[EmailStr, Body(embed=True)],
    quota: Annotated[UserQuota, Body(embed=True)],
    *,
    force: Annotated[bool, Body(embed=True)] = False,
) -> UserQuota:
    _user = await User.by_email(email)
    if _user is None:
        raise HTTPException(status_code=401, detail="Incorrect username")
    if force or quota.custom_quota_expire_date is not None:
        _user.custom_quota_expire_date = quota.custom_quota_expire_date
    if force or quota.custom_quota_duration is not None:
        _user.custom_quota_duration = quota.custom_quota_duration
    if force or quota.custom_quota_storage is not None:
        _user.custom_quota_storage = quota.custom_quota_storage
    await _user.save_changes()
    # TODO: inform user about it?
    # TODO: logic should go to into user-model
    return _user


# ###############################################################
# Password Management
# ###############################################################


@router.post("/forgot-password")
async def forgot_password(
    email: Annotated[EmailStr, Body(embed=True)],
) -> Response:
    """Send password reset email."""
    user = await User.by_email(email)
    if user is None:
        return Response(status_code=200)
    user.token_pw_reset = calculate_hash(user.email + str(local_now()))[-12:]  # => unstable token
    await get_mail_engine().send_password_reset_email(email, user.token_pw_reset)
    await user.save_changes()  # mail is sent first!
    return Response(status_code=200)


@router.get("/reset-password")
@router.post("/reset-password")
async def reset_password(
    token: Annotated[str, Body(embed=True)],
    password: Annotated[PasswordStr, Body(embed=True)],
) -> UserOut:
    """Reset user password from token value."""
    user = await User.by_reset_token(token)
    if user is None:
        raise HTTPException(404, "Invalid password reset token")
    user.password_hash = calculate_password_hash(password)
    user.token_pw_reset = None
    await user.save_changes()
    return user


# ###############################################################
# Account Handling
# ###############################################################


@router.post("/approve", dependencies=[Depends(active_admin_user)])
async def approve(
    email: Annotated[EmailStr, Body(embed=True)],
) -> Response:
    """Pre-Approve Email-Address for registration - also functions as validation.

    If Mail-System does not work, the admin can hand token to user manually (returned here).
    """
    user = await User.by_email(email)
    if user is not None:
        raise HTTPException(409, "Account already exists")
    user = User(
        email=email,
        password_hash="",  # placeholder not usable for long
        token_verification=calculate_hash(email)[-12:],  # without date -> stable token
        role=UserRole.user,
    )
    await get_mail_engine().send_approval_email(email, user.token_verification)
    await User.insert_one(user)  # mail is sent first!
    return Response(status_code=200, content=user.token_verification)


@router.post("/register")
async def user_registration(
    user_reg: UserRegistration,
) -> UserOut:
    """Create a new user.

    To avoid spam / misuse, a valid token (generated from email) is needed.
    """
    user = await User.by_email(user_reg.email)
    if user_reg.token is None:
        raise HTTPException(404, "Invalid registration-token")
    if (user is None) or (user.token_verification != user_reg.token):
        raise HTTPException(404, "Invalid account registration")
    if user.email_confirmed_at is not None:
        raise HTTPException(409, "Invalid user registration - account is already confirmed")
    user.password_hash = calculate_password_hash(user_reg.password)
    user.disabled = False
    user.email_confirmed_at = local_now()
    user.token_verification = None
    await get_mail_engine().send_registration_complete_email(user_reg.email)
    await user.save_changes()  # mail is sent first!
    return user


@router.get("/verify/{token}")
@router.post("/verify/{token}")
async def verify_email(
    token: str,
) -> Response:
    """Verify the user's email with the supplied token.

    NOTE: currently only used for admins.
    """
    user = await User.by_verification_token(token)
    if user is None:
        raise HTTPException(404, "Token not found")
    if user.email_confirmed_at is not None:
        # This should never happen,
        # because no verification token can be generated for verified accounts
        raise HTTPException(409, "Email is already verified")
    user.email_confirmed_at = local_now()
    user.token_verification = None
    user.disabled = False
    await get_mail_engine().send_registration_complete_email(user.email)
    await user.save_changes()  # mail is sent first!
    return Response(status_code=200, content="Verification successful")


@router.post("/change_state", dependencies=[Depends(active_admin_user)])
async def change_state(
    email: Annotated[EmailStr, Body(embed=True)],
    enabled: Annotated[bool, Body(embed=True)],
) -> Response:
    """Pre-Approve Email-Address for registration - also functions as validation.

    If Mail-System does not work, the admin can hand token to user manually (returned here).
    """
    user = await User.by_email(email)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect username")
    user.disabled = not enabled
    await user.save_changes()
    # TODO: inform user about it?
    return Response(status_code=200, content="State-Change successful")


# TODO: allow elevating users & add this to Client


@router.get("/all", dependencies=[Depends(active_admin_user)])
async def list_all_users() -> list[UserOut]:
    # not the most elegant solution, but this is admin-only anyway
    return await User.all().to_list()
