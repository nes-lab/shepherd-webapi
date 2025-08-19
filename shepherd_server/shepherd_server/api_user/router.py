from typing import Annotated

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from pydantic import EmailStr
from shepherd_core import local_now
from shepherd_core.data_models import Experiment

from shepherd_server.api_experiment.models import WebExperiment

from .models import PasswordStr
from .models import User
from .models import UserOut
from .models import UserQuota
from .models import UserRegistration
from .models import UserRole
from .models import UserUpdate
from .utils_mail import MailEngine
from .utils_mail import mail_engine
from .utils_misc import active_user_is_admin
from .utils_misc import calculate_hash
from .utils_misc import calculate_password_hash
from .utils_misc import current_active_user

router = APIRouter(prefix="/user", tags=["User"])


# ###############################################################
# Own Data Access
# ###############################################################


@router.get("")
async def user_info(user: Annotated[User, Depends(current_active_user)]) -> UserOut:
    user.storage_available = user.quota_storage - await WebExperiment.get_storage(user)
    await user.save_changes()
    return user


@router.patch("")
async def update_user(
    update: UserUpdate, user: Annotated[User, Depends(current_active_user)]
) -> UserOut:
    """Update allowed user fields."""
    fields = update.model_dump(exclude_unset=True)
    new_email = fields.pop("email", None)
    if isinstance(new_email, str) and new_email != user.email:
        if await User.by_email(new_email) is not None:
            raise HTTPException(406, "Email already exists")
        user.update_email(new_email)
    user = user.model_copy(update=fields)
    await user.save()
    return user


@router.delete("")
async def delete_user(
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    """Delete current user and its experiments & content."""

    experiments = await Experiment.get_by_user(user)
    for xp in experiments:
        await xp.delete_content()
        await xp.delete()
    await user.delete()
    # TODO: inform user about it
    return Response(status_code=204)


# ###############################################################
# Quota
# ###############################################################


@router.patch("/quota", dependencies=[Depends(active_user_is_admin)])
async def update_quota(
    email: Annotated[EmailStr, Body(embed=True)],
    quota: Annotated[UserQuota, Body(embed=True)],
) -> UserQuota:
    _user = await User.by_email(email)
    if _user is None:
        raise HTTPException(status_code=401, detail="Incorrect username")
    if quota.custom_quota_expire_date is not None:
        _user.custom_quota_expire_date = quota.custom_quota_expire_date
    if quota.custom_quota_duration is not None:
        _user.custom_quota_duration = quota.custom_quota_duration
    if quota.custom_quota_storage is not None:
        _user.custom_quota_storage = quota.custom_quota_storage
    await _user.save_changes()
    # TODO: inform user about it?
    return _user


# ###############################################################
# Password Management
# ###############################################################


@router.post("/forgot-password")
async def forgot_password(
    email: Annotated[EmailStr, Body(embed=True)],
    mail_sys: Annotated[MailEngine, Depends(mail_engine)],
) -> Response:
    """Send password reset email."""
    user = await User.by_email(email)
    if user is None:
        return Response(status_code=200)
    user.token_pw_reset = calculate_hash(user.email + str(local_now()))[-12:]
    await mail_sys.send_password_reset_email(email, user.token_pw_reset)
    await user.save_changes()
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
    await user.save_changes()
    return user


# ###############################################################
# Account Handling
# ###############################################################


@router.post("/approve", dependencies=[Depends(active_user_is_admin)])
async def approve(
    email: Annotated[EmailStr, Body(embed=True)],
    mail_sys: Annotated[MailEngine, Depends(mail_engine)],
) -> Response:
    """Pre-Approve Email-Address for registration - also functions as validation.

    If Mail-System does not work, the admin can hand token to user manually (returned here).
    """
    user = await User.by_email(email)
    if user is not None:
        raise HTTPException(409, "Account already exists")
    token_verification = calculate_hash(email)[-12:]
    await mail_sys.send_approval_email(email, token_verification)
    return Response(status_code=200, content=token_verification)


@router.post("/register")
async def user_registration(
    user_reg: UserRegistration,
    mail_sys: Annotated[MailEngine, Depends(mail_engine)],
) -> UserOut:
    """Create a new user.

    To avoid spam / misuse, a valid token (generated from email) is needed.
    """
    token_sys = calculate_hash(user_reg.email)[-12:]
    if token_sys != user_reg.token:
        raise HTTPException(404, "Invalid user registration token")
    user = await User.by_email(user_reg.email)
    if user is not None:
        raise HTTPException(409, "User with that email already exists")
    pw_hash = calculate_password_hash(user_reg.password)
    user = User(
        email=user_reg.email,
        password_hash=pw_hash,
        disabled=False,
        email_confirmed_at=local_now(),
        token_verification=None,
        role=UserRole.user,
    )
    await user.create()
    await mail_sys.send_registration_complete_email(user_reg.email)
    return user


@router.get("/verify/{token}")
@router.post("/verify/{token}")
async def verify_email(
    token: str,
    mail_sys: Annotated[MailEngine, Depends(mail_engine)],
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
    await mail_sys.send_registration_complete_email(user.email)
    await user.save_changes()
    return Response(status_code=200, content="Verification successful")


@router.post("/change_state", dependencies=[Depends(active_user_is_admin)])
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
    user.save_changes()
    # TODO: inform user about it?
    return Response(status_code=200, content="State-Change successful")
