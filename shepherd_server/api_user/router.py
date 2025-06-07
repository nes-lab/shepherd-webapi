from typing import Annotated

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from pydantic import EmailStr
from shepherd_core import local_now

from .models import PasswordStr
from .models import User
from .models import UserAuth
from .models import UserOut
from .models import UserQuota
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
            raise HTTPException(400, "Email already exists")
        user.update_email(new_email)
    user = user.model_copy(update=fields)
    await user.save()
    return user


@router.delete("")
async def delete_user(
    user: Annotated[User, Depends(current_active_user)],
) -> Response:
    """Delete current user."""
    await User.find_one(User.email == user.email).delete()
    return Response(status_code=204)


# ###############################################################
# Quota
# ###############################################################


@router.get("/quota")
async def quota_info(user: Annotated[User, Depends(current_active_user)]) -> UserQuota:
    return user


@router.patch("/quota", dependencies=[Depends(active_user_is_admin)])
async def update_quota(
    email: Annotated[EmailStr, Body(embed=True)],
    quota: Annotated[UserQuota, Body(embed=True)],
) -> UserQuota:
    _user = await User.by_email(email)
    if _user is None:
        raise HTTPException(status_code=401, detail="Incorrect username")
    if quota.quota_expire_date is not None:
        _user.quota_expire_date = quota.quota_expire_date
    if quota.quota_custom_duration is not None:
        _user.quota_custom_duration = quota.quota_custom_duration
    if quota.quota_custom_storage is not None:
        _user.quota_custom_storage = quota.quota_custom_storage
    await _user.save()
    return _user


# ###############################################################
# Registration
# ###############################################################


@router.post("/register")
async def user_registration(
    user_auth: UserAuth,
    mail_engine: Annotated[MailEngine, Depends(mail_engine)],
) -> UserOut:
    """Create a new user."""
    # TODO: ip-based rate-limit needed (3/d), otherwise this is going to be misused
    user = await User.by_email(user_auth.email)
    if user is not None:
        raise HTTPException(409, "User with that email already exists")
    pw_hash = calculate_password_hash(user_auth.password)
    token_verification = calculate_hash(user_auth.email + str(local_now()))[:10]
    await mail_engine.send_verification_email(user_auth.email, token_verification)
    user = User(
        email=user_auth.email,
        password_hash=pw_hash,
        token_verification=token_verification,
        disabled=True,
    )
    await user.create()
    return user


@router.post("/forgot-password")
async def forgot_password(
    email: Annotated[EmailStr, Body(embed=True)],
    mail_engine: Annotated[MailEngine, Depends(mail_engine)],
) -> Response:
    """Send password reset email."""
    user = await User.by_email(email)
    if user is None:
        return Response(status_code=200)
    user.token_pw_reset = calculate_hash(user.email + str(local_now()))[:10]
    await mail_engine.send_password_reset_email(email, user.token_pw_reset)
    await user.save()
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
    await user.save()
    return user


# ###############################################################
# Verification
# ###############################################################


@router.get("/verify/{token}")
@router.post("/verify/{token}")
async def verify_email(
    token: str,
    mail_engine: Annotated[MailEngine, Depends(mail_engine)],
) -> Response:
    """Verify the user's email with the supplied token."""
    user = await User.by_verification_token(token)
    if user is None:
        raise HTTPException(404, "Token not found")
    if user.email_confirmed_at is not None:
        # This should never happen,
        # because no verification token can be generated for verified accounts
        raise HTTPException(412, "Email is already verified")
    user.email_confirmed_at = local_now()
    user.token_verification = None
    await mail_engine.send_approval_request_email(user.email)
    await user.save()
    return Response(status_code=200)


@router.get("/approve", dependencies=[Depends(active_user_is_admin)])
@router.post("/approve", dependencies=[Depends(active_user_is_admin)])
async def approve(
    email: Annotated[EmailStr, Body(embed=True)],
) -> Response:
    user = await User.by_email(email)
    if user is None:
        return Response(status_code=404)
    user.disabled = False
    await user.save()
    return Response(status_code=200)
