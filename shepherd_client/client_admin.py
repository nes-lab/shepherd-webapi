from pydantic import EmailStr
from pydantic import HttpUrl
from pydantic import validate_call

from .client_user import UserClient
from .config import PasswordStr


class AdminClient(UserClient):
    @validate_call
    def __init__(
        self,
        server: HttpUrl | None = None,
        admin_email: EmailStr | None = None,
        password: PasswordStr | None = None,
        *,
        save_credentials: bool = False,
    ) -> None:
        super().__init__(
            server=server,
            user_email=admin_email,
            password=password,
            save_credentials=save_credentials,
            debug=True,
        )

        # TODO: forbid registering
        # TODO: allow raising quota
        # TODO: approve user
        #
