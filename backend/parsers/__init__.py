from parsers.robinhood import RobinhoodParser
from parsers.schwab import SchwabParser
from parsers.fidelity import FidelityParser
from parsers.vanguard import VanguardParser
from parsers.webull import WebullParser
from parsers.etrade import ETradeParser

PARSERS = {
    "robinhood": RobinhoodParser(),
    "schwab": SchwabParser(),
    "fidelity": FidelityParser(),
    "vanguard": VanguardParser(),
    "webull": WebullParser(),
    "etrade": ETradeParser(),
}


def get_parser(broker: str):
    return PARSERS.get(broker.lower())
