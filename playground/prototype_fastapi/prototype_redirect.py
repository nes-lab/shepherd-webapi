"""
run with: uvicorn prototype_redirect:app --reload
run with: python3 ./prototype_redirect.py
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse

use_ssl = True

app = FastAPI(
    title="shepherd-web-redirect",
    version="2023.09.21",
    redoc_url=None,
    docs_url=None,
)

if use_ssl:
    app.add_middleware(HTTPSRedirectMiddleware)


@app.get("/")
async def redir():
    return RedirectResponse("https://orgua.github.io/shepherd/testbed/instance_tud.html")


if __name__ == "__main__":
    uvi_args = {
        "app": "prototype_redirect:app",
        "reload": False,
        "port": 443 if use_ssl else 80,
        "host": "shepherd.cfaed.tu-dresden.de",
    }
    if use_ssl:
        uvi_args["ssl_keyfile"] = "/etc/shepherd/ssl_private_key.pem"
        uvi_args["ssl_certfile"] = "/etc/shepherd/ssl_certificate.pem"
        uvi_args["ssl_ca_certs"] = "/etc/shepherd/ssl_ca_certs.pem"

    uvicorn.run(**uvi_args)
