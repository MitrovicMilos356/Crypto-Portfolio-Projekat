

from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class Finding:
    #jedan zabelezeni ishod tokom testa
    kind: str          # "exposed" | "blocked" | "info"
    message: str


@dataclass
class TestContext:
    #sve sto modul dobija od GUI-ja tokom jednog pokretanja
    target: str
    _log: Callable[[str], None]
    findings: List[Finding] = field(default_factory=list)

    def log(self, text: str = "") -> None:
        #ispisuje red u konzolu GUI-ja
        self._log(text)

    def exposed(self, message: str) -> None:
        #test je uspeo da dodje do podatka koji nije smeo da bude dostupan
        self.findings.append(Finding("exposed", message))
        self._log(f"[RANJIVO] {message}")

    def blocked(self, message: str) -> None:
        #aplikacija je ispravno odbila/zaustavila pokusaj
        self.findings.append(Finding("blocked", message))
        self._log(f"[OK]      {message}")

    def info(self, message: str) -> None:
        #neutralna informacija o toku testa
        self.findings.append(Finding("info", message))
        self._log(f"[info]    {message}")

    def summary(self) -> str:
        #kratak zakljucak na kraju testa
        exposed = sum(1 for f in self.findings if f.kind == "exposed")
        blocked = sum(1 for f in self.findings if f.kind == "blocked")
        if exposed and not blocked:
            return f"REZULTAT: ranjivo ({exposed} izlozenih tacaka)."
        if blocked and not exposed:
            return f"REZULTAT: zasticeno ({blocked} blokiranih pokusaja)."
        if exposed and blocked:
            return f"REZULTAT: delimicno ({exposed} izlozenih, {blocked} blokiranih)."
        return "REZULTAT: nema nalaza (vidi log iznad)."
