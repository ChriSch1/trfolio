import logging

class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",    # grey
        "INFO": "\033[94m",     # blue
        "SUCCESS": "\033[92m",  # green (custom level)
        "WARNING": "\033[93m",  # yellow
        "ERROR": "\033[91m",    # red
        "CRITICAL": "\033[95m", # magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def setup_logger(name: str = "trfolio") -> logging.Logger:
    """Set up and return a colored logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = ColorFormatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def parse_money(s: str) -> float:
    '''
    The invoices seem to be inconsistent switching between international
    number notation and european. This function helps to safely parse the str
    into numbers
    '''
    s = s.strip()
    s = s.replace(' ', '').replace('\xa0', '')  # no-break spaces from PDFs
    if ',' in s:
        # European style: 1.234,56 or 123,45 or -1.234,56
        s = s.replace('.', '').replace(',', '.')
    # Normalize leading plus, and handle thousands-only numbers
    return float(s)