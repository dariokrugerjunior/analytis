"""FIFA continental confederation classification."""

from enum import StrEnum


class Confederation(StrEnum):
    UEFA = "UEFA"
    CONMEBOL = "CONMEBOL"
    CONCACAF = "CONCACAF"
    AFC = "AFC"
    CAF = "CAF"
    OFC = "OFC"
    UNKNOWN = "UNKNOWN"


_COUNTRY_TO_CONFED: dict[str, Confederation] = {
    # CONMEBOL (10)
    "ARG": Confederation.CONMEBOL,
    "BOL": Confederation.CONMEBOL,
    "BRA": Confederation.CONMEBOL,
    "CHI": Confederation.CONMEBOL,
    "COL": Confederation.CONMEBOL,
    "ECU": Confederation.CONMEBOL,
    "PAR": Confederation.CONMEBOL,
    "PER": Confederation.CONMEBOL,
    "URU": Confederation.CONMEBOL,
    "VEN": Confederation.CONMEBOL,
    # CONCACAF
    "MEX": Confederation.CONCACAF,
    "USA": Confederation.CONCACAF,
    "CAN": Confederation.CONCACAF,
    "CRC": Confederation.CONCACAF,
    "HON": Confederation.CONCACAF,
    "PAN": Confederation.CONCACAF,
    "JAM": Confederation.CONCACAF,
    "HAI": Confederation.CONCACAF,
    "SLV": Confederation.CONCACAF,
    "TRI": Confederation.CONCACAF,
    # CAF
    "MAR": Confederation.CAF,
    "SEN": Confederation.CAF,
    "EGY": Confederation.CAF,
    "NGA": Confederation.CAF,
    "CMR": Confederation.CAF,
    "GHA": Confederation.CAF,
    "TUN": Confederation.CAF,
    "ALG": Confederation.CAF,
    "RSA": Confederation.CAF,
    "CIV": Confederation.CAF,
    "MLI": Confederation.CAF,
    # AFC
    "JPN": Confederation.AFC,
    "KOR": Confederation.AFC,
    "AUS": Confederation.AFC,
    "IRN": Confederation.AFC,
    "KSA": Confederation.AFC,
    "QAT": Confederation.AFC,
    "UAE": Confederation.AFC,
    "IRQ": Confederation.AFC,
    "UZB": Confederation.AFC,
    "CHN": Confederation.AFC,
    # OFC
    "NZL": Confederation.OFC,
    "FIJ": Confederation.OFC,
    "SOL": Confederation.OFC,
    "VAN": Confederation.OFC,
    # UEFA
    "FRA": Confederation.UEFA,
    "GER": Confederation.UEFA,
    "ESP": Confederation.UEFA,
    "ITA": Confederation.UEFA,
    "ENG": Confederation.UEFA,
    "POR": Confederation.UEFA,
    "NED": Confederation.UEFA,
    "BEL": Confederation.UEFA,
    "CRO": Confederation.UEFA,
    "POL": Confederation.UEFA,
    "DEN": Confederation.UEFA,
    "SUI": Confederation.UEFA,
    "AUT": Confederation.UEFA,
    "SWE": Confederation.UEFA,
    "NOR": Confederation.UEFA,
    "CZE": Confederation.UEFA,
    "TUR": Confederation.UEFA,
    "SCO": Confederation.UEFA,
    "WAL": Confederation.UEFA,
    "SRB": Confederation.UEFA,
    "UKR": Confederation.UEFA,
    "RUS": Confederation.UEFA,
    "GRE": Confederation.UEFA,
    "ROU": Confederation.UEFA,
    "HUN": Confederation.UEFA,
    "BIH": Confederation.UEFA,
    "ISL": Confederation.UEFA,
    "FIN": Confederation.UEFA,
    "IRL": Confederation.UEFA,
    "NIR": Confederation.UEFA,
    "ALB": Confederation.UEFA,
    "SVK": Confederation.UEFA,
    "SVN": Confederation.UEFA,
    "BUL": Confederation.UEFA,
}


def confederation_of_country(country_code: str) -> Confederation:
    """Map ISO-3 country code to FIFA confederation."""
    return _COUNTRY_TO_CONFED.get(country_code.upper(), Confederation.UNKNOWN)


__all__ = ["Confederation", "confederation_of_country"]
