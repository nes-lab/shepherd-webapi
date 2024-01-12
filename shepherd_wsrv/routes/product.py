from fastapi import APIRouter, Depends
from fastui import FastUI, AnyComponent, components as cs, prebuilt_html
from fastui.components.display import DisplayLookup
from fastui.events import GoToEvent, BackEvent
from starlette.responses import HTMLResponse

from shepherd_wsrv.data_models.product import Product
from shepherd_wsrv.routes.auth import oauth2_scheme

router = APIRouter(prefix="/product", tags=["Product"])


@router.get("/items")
async def read_products(token: str = Depends(oauth2_scheme)):
    # TODO
    #products = await Product.find(Product.price > 0).to_list()
    products = await Product.find().to_list()
    #products_j = [_p.model_dump_json() for _p in products]
    #Product().model_dump_json()
    return {"token": token,
        "value": products,
            }

"""
@router.get("/witems", response_model=FastUI, response_model_exclude=None)
async def wread_products() -> list[AnyComponent]:
    # TODO
    products = await Product.find().to_list()
    return [
        cs.Page(
            components=[
                cs.Heading(text="Products", level=2),
                cs.Table(
                    data=products,
                    columns=[
                        DisplayLookup(field="name", on_click=GoToEvent(url="/product/{name}")),
                        DisplayLookup(field="price"),
                        DisplayLookup(field="category"),
                    ]
                )
            ]
        )
    ]


@router.get("/{product_id}", response_model=FastUI, response_model_exclude=None)
async def get_product(product_id: str) -> list[AnyComponent]:
    _p = await Product.get(product_id)
    #return {"value": _p}
    return [
        cs.Page(
            components=[
                cs.Heading(text=_p.name, level=2),
                cs.Link(components=[cs.Text(text='Back')], on_click=BackEvent()),
                cs.Details(data=_p),
            ]
        ),
    ]
"""


@router.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    """Simple HTML page which serves the React app, comes last as it matches all paths."""
    return HTMLResponse(prebuilt_html(title='FastUI Demo'))

