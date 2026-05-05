# Must import before migrations command runs, otherwise it will not detect the models
from app.account import models as account_models
from app.product import models as product_models
from app.cart import models as card_models
from app.shipping import models as shipping_models