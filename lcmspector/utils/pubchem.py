"""
PubChem lookup worker for compound mass lookup.

Provides a QObject-based worker for fetching compound data from PubChem
in a background thread to avoid blocking the UI.
"""

import logging
import traceback
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

# Proton mass for ionization calculations
PROTON_MASS = 1.007276


class PubChemLookupWorker(QObject):
    """
    Worker for looking up compound data from PubChem.

    Designed to run in a QThread. Emits finished or error signals
    when the lookup completes.

    Signals
    -------
    finished : Signal(str, dict)
        Emitted on successful lookup. Args: (compound_name, data_dict)
        data_dict contains: exact_mass, mz_pos, mz_neg, iupac_name
    error : Signal(str, str)
        Emitted on lookup failure. Args: (compound_name, error_message)
    """

    finished = Signal(str, dict)  # compound_name, {exact_mass, mz_pos, mz_neg, iupac_name}
    error = Signal(str, str)  # compound_name, error_message

    def __init__(self, compound_name: str, parent=None):
        super().__init__(parent)
        self.compound_name = compound_name
        self._timeout = 10  # seconds

    def run(self):
        """
        Execute the PubChem lookup.

        Fetches compound properties from PubChem and calculates
        [M+H]+ and [M-H]- m/z values.
        """
        logger.debug(f"Starting PubChem lookup for '{self.compound_name}'")

        try:
            import pubchempy as pcp

            # Query PubChem for compound properties
            logger.debug(f"Querying PubChem API for '{self.compound_name}'")
            results = pcp.get_properties(
                ["IUPACName", "ExactMass", "MolecularFormula"],
                self.compound_name,
                namespace="name",
            )

            logger.debug(f"Raw PubChem response: {results}")

            if not results:
                logger.warning(f"Compound not found on PubChem: '{self.compound_name}'")
                self.error.emit(self.compound_name, "Compound not found on PubChem")
                return

            # Extract data from first result
            compound_data = results[0]
            exact_mass_str = compound_data.get("ExactMass")
            iupac_name = compound_data.get("IUPACName", "")

            if not exact_mass_str:
                logger.warning(
                    f"No exact mass found for '{self.compound_name}'"
                )
                self.error.emit(self.compound_name, "No exact mass available")
                return

            exact_mass = float(exact_mass_str)

            # Calculate ionization m/z values
            mz_pos = round(exact_mass + PROTON_MASS, 4)  # [M+H]+
            mz_neg = round(exact_mass - PROTON_MASS, 4)  # [M-H]-

            result_data = {
                "exact_mass": exact_mass,
                "mz_pos": mz_pos,
                "mz_neg": mz_neg,
                "iupac_name": iupac_name,
                "molecular_formula": compound_data.get("MolecularFormula", ""),
            }

            logger.info(
                f"PubChem lookup successful for '{self.compound_name}': "
                f"exact_mass={exact_mass}, [M+H]+={mz_pos}, [M-H]-={mz_neg}"
            )
            self.finished.emit(self.compound_name, result_data)

        except ImportError:
            logger.error("pubchempy not installed")
            self.error.emit(self.compound_name, "pubchempy library not installed")

        except TimeoutError:
            logger.warning(f"PubChem lookup timed out for '{self.compound_name}'")
            self.error.emit(self.compound_name, "Request timed out")

        except ConnectionError as e:
            logger.error(
                f"Network error during PubChem lookup for '{self.compound_name}': {e}\n"
                f"{traceback.format_exc()}"
            )
            self.error.emit(self.compound_name, f"Network error: {e}")

        except Exception as e:
            logger.error(
                f"Unexpected error during PubChem lookup for '{self.compound_name}': {e}\n"
                f"{traceback.format_exc()}"
            )
            self.error.emit(self.compound_name, f"Lookup failed: {e}")
