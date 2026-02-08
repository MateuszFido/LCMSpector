"""
Theoretical isotopic mass spectrum prediction.

Provides formula detection, isotopic pattern calculation using pyteomics,
and data structures for theoretical spectra with common adducts.
Supports molecular formulas, peptide sequences, and compound name lookup.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
from pyteomics.mass import Composition, fast_mass, isotopologues, nist_mass
from pyteomics.auxiliary import PyteomicsError

logger = logging.getLogger(__name__)

# Standard 20 amino acids (single-letter codes)
STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")


@dataclass
class AdductSpectrum:
    """Isotopic pattern for a single adduct type.

    Attributes
    ----------
    mz_values : np.ndarray
        Isotopic peak m/z values (sorted ascending).
    abundances : np.ndarray
        Relative abundances normalized so max = 1.0.
    monoisotopic_mz : float
        Monoisotopic m/z for this adduct.
    """

    mz_values: np.ndarray
    abundances: np.ndarray
    monoisotopic_mz: float


@dataclass
class TheoreticalSpectrum:
    """Theoretical isotopic spectrum for a compound.

    Attributes
    ----------
    formula : str
        Molecular formula used for calculation.
    adducts : dict[str, AdductSpectrum]
        Mapping of adduct label to its isotopic pattern.
    """

    formula: str
    adducts: dict


@dataclass
class PeptideFragment:
    """A single b or y fragment ion.

    Attributes
    ----------
    label : str
        Fragment label (e.g. "b3", "y5").
    mz : float
        Monoisotopic m/z value.
    ion_type : str
        "b" or "y".
    position : int
        Cleavage position (1-indexed).
    """

    label: str
    mz: float
    ion_type: str
    position: int


@dataclass
class PeptideSpectrum:
    """Theoretical spectrum for a peptide sequence.

    Attributes
    ----------
    sequence : str
        Amino acid sequence.
    fragments : list[PeptideFragment]
        b and y fragment ions.
    precursor_isotopes : dict[str, AdductSpectrum]
        Isotopic envelopes for each adduct, same structure as
        TheoreticalSpectrum.adducts.
    """

    sequence: str
    fragments: list
    precursor_isotopes: dict


@dataclass
class AdductDefinition:
    """Definition for a single adduct type.

    Attributes
    ----------
    label : str
        Display label (e.g. "[M+H]+").
    add_formula : str
        Atoms to add (e.g. "H", "Na"). Empty string for none.
    subtract_formula : str
        Atoms to subtract (e.g. "H", "H2O"). Empty string for none.
    charge : int
        Absolute charge state (1, 2, ...).
    polarity : str
        "positive" or "negative".
    multiplier : int
        Molecule multiplier (1=monomer, 2=dimer).
    default_checked : bool
        Whether this adduct is checked by default.
    """

    label: str
    add_formula: str
    subtract_formula: str
    charge: int
    polarity: str
    multiplier: int
    default_checked: bool


# Single source of truth for all supported adducts
ADDUCT_DEFINITIONS: dict[str, AdductDefinition] = {}

_adduct_list = [
    # Positive mode
    AdductDefinition("[M+H]+", "H", "", 1, "positive", 1, True),
    AdductDefinition("[M+Na]+", "Na", "", 1, "positive", 1, False),
    AdductDefinition("[M+K]+", "K", "", 1, "positive", 1, False),
    AdductDefinition("[M+NH4]+", "NH4", "", 1, "positive", 1, False),
    AdductDefinition("[M+2H]2+", "H2", "", 2, "positive", 1, False),
    AdductDefinition("[2M+H]+", "H", "", 1, "positive", 2, False),
    AdductDefinition("[M+H-H2O]+", "H", "H2O", 1, "positive", 1, False),
    # Negative mode
    AdductDefinition("[M-H]-", "", "H", 1, "negative", 1, True),
    AdductDefinition("[M+Cl]-", "Cl", "", 1, "negative", 1, False),
    AdductDefinition("[M+HCOO]-", "CHO2", "", 1, "negative", 1, False),
    AdductDefinition("[M+CH3COO]-", "C2H3O2", "", 1, "negative", 1, False),
    AdductDefinition("[M-2H]2-", "", "H2", 2, "negative", 1, False),
    AdductDefinition("[2M-H]-", "", "H", 1, "negative", 2, False),
]

for _defn in _adduct_list:
    ADDUCT_DEFINITIONS[_defn.label] = _defn

DEFAULT_ADDUCTS = [k for k, v in ADDUCT_DEFINITIONS.items() if v.default_checked]


def compute_adduct_composition(base_comp: Composition, defn: AdductDefinition) -> Composition:
    """Build full composition for an adduct (base * multiplier + add - subtract).

    Parameters
    ----------
    base_comp : Composition
        Base molecular composition.
    defn : AdductDefinition
        Adduct definition to apply.

    Returns
    -------
    Composition
        The modified composition for this adduct.
    """
    comp = base_comp * defn.multiplier
    if defn.add_formula:
        comp = comp + Composition(formula=defn.add_formula)
    if defn.subtract_formula:
        comp = comp - Composition(formula=defn.subtract_formula)
    return comp


def compute_adduct_mz(base_comp: Composition, defn: AdductDefinition) -> float:
    """Fast monoisotopic m/z via Composition.mass() / charge.

    Parameters
    ----------
    base_comp : Composition
        Base molecular composition.
    defn : AdductDefinition
        Adduct definition to apply.

    Returns
    -------
    float
        Monoisotopic m/z value.
    """
    return compute_adduct_composition(base_comp, defn).mass() / defn.charge


def calculate_monoisotopic_mz(formula: str, adduct_types: list[str]) -> dict[str, float]:
    """Fast path: dict of {adduct_label: monoisotopic_mz} for table display.

    Uses ``Composition.mass()`` (~6.5us) instead of ``isotopologues()`` (~3.7ms).

    Parameters
    ----------
    formula : str
        Molecular formula (e.g. "C8H10N4O2").
    adduct_types : list[str]
        Adduct labels to compute (e.g. ["[M+H]+", "[M-H]-"]).

    Returns
    -------
    dict[str, float]
        Mapping of adduct label to rounded monoisotopic m/z.
    """
    base_comp = Composition(formula=formula)
    result = {}
    for label in adduct_types:
        defn = ADDUCT_DEFINITIONS.get(label)
        if defn is not None:
            result[label] = round(compute_adduct_mz(base_comp, defn), 4)
    return result


def is_valid_peptide(text: str) -> bool:
    """Check if text is a valid peptide sequence (standard 20 amino acids).

    Parameters
    ----------
    text : str
        Text to check (should be pre-stripped).

    Returns
    -------
    bool
        True if text looks like a peptide sequence.
    """
    if len(text) < 2:
        return False
    return all(c in STANDARD_AMINO_ACIDS for c in text)


def detect_input_type(user_input: str) -> str:
    """Determine whether user input is a molecular formula, peptide, or compound name.

    Parameters
    ----------
    user_input : str
        Text entered by the user (e.g. "C8H10N4O2", "PEPTIDE", or "Caffeine").

    Returns
    -------
    str
        ``"formula"``, ``"peptide"``, or ``"name"``.
    """
    if not user_input or not user_input.strip():
        return "name"

    text = user_input.strip()

    # Lowercase first character -> name
    if text[0].islower():
        return "name"

    # Contains spaces -> name
    if " " in text:
        return "name"

    # Try parsing as a formula
    try:
        comp = Composition(formula=text)
    except (PyteomicsError, Exception):
        comp = None

    if comp:
        # Verify all parsed elements exist in nist_mass
        all_valid = all(element in nist_mass for element in comp)
        if all_valid:
            try:
                mass = comp.mass()
                if mass > 0:
                    return "formula"
            except (PyteomicsError, Exception) as exc:
                # Failed to compute mass; treat input as non-formula and fall through.
                logger.debug("Failed to compute mass for parsed composition %r: %s", comp, exc)

    # Check for peptide sequence (formula takes priority)
    if is_valid_peptide(text):
        return "peptide"

    return "name"


def calculate_theoretical_spectrum(
    formula: str,
    adduct_types: list[str] | None = None,
    abundance_threshold: float = 0.001,
) -> TheoreticalSpectrum:
    """Calculate theoretical isotopic spectrum for a molecular formula.

    Parameters
    ----------
    formula : str
        Molecular formula (e.g. "C8H10N4O2").
    adduct_types : list[str], optional
        Adduct types to compute. Default: ``DEFAULT_ADDUCTS``.
    abundance_threshold : float, optional
        Minimum relative abundance to include. Default: 0.001.

    Returns
    -------
    TheoreticalSpectrum
        Computed isotopic patterns for each adduct.

    Raises
    ------
    ValueError
        If the formula is invalid or cannot be parsed.
    """
    if adduct_types is None:
        adduct_types = DEFAULT_ADDUCTS

    # Validate formula
    try:
        base_comp = Composition(formula=formula)
    except (PyteomicsError, Exception) as e:
        raise ValueError(f"Invalid formula '{formula}': {e}") from e

    if not base_comp:
        raise ValueError(f"Empty formula: '{formula}'")

    for element in base_comp:
        if element not in nist_mass:
            raise ValueError(f"Unknown element '{element}' in formula '{formula}'")

    adducts = {}

    for adduct_type in adduct_types:
        defn = ADDUCT_DEFINITIONS.get(adduct_type)
        if defn is None:
            logger.warning(f"Unsupported adduct type: {adduct_type}")
            continue

        try:
            adduct_comp = compute_adduct_composition(base_comp, defn)

            # Compute isotopologues
            isos = list(
                isotopologues(
                    composition=adduct_comp,
                    report_abundance=True,
                    overall_threshold=abundance_threshold,
                )
            )

            if not isos:
                continue

            # Extract m/z and abundances
            mz_list = []
            abundance_list = []
            for iso_comp, abundance in isos:
                mz_list.append(iso_comp.mass() / defn.charge)
                abundance_list.append(abundance)

            mz_array = np.array(mz_list)
            abundance_array = np.array(abundance_list)

            # Sort by m/z
            sort_idx = np.argsort(mz_array)
            mz_array = mz_array[sort_idx]
            abundance_array = abundance_array[sort_idx]

            # Normalize so max = 1.0
            max_abundance = abundance_array.max()
            if max_abundance > 0:
                abundance_array = abundance_array / max_abundance

            # Monoisotopic m/z is the lowest m/z (most abundant isotope)
            monoisotopic_mz = mz_array[0]

            adducts[adduct_type] = AdductSpectrum(
                mz_values=mz_array,
                abundances=abundance_array,
                monoisotopic_mz=monoisotopic_mz,
            )

        except Exception as e:
            logger.warning(f"Failed to compute {adduct_type} for '{formula}': {e}")
            continue

    return TheoreticalSpectrum(formula=formula, adducts=adducts)


def calculate_peptide_precursor_mz(
    sequence: str, adduct_types: list[str] | None = None
) -> dict[str, float]:
    """Fast path: dict of {adduct_label: monoisotopic_mz} for a peptide sequence.

    Parameters
    ----------
    sequence : str
        Amino acid sequence (e.g. "PEPTIDE").
    adduct_types : list[str], optional
        Adduct labels to compute. Default: ``DEFAULT_ADDUCTS``.

    Returns
    -------
    dict[str, float]
        Mapping of adduct label to rounded monoisotopic m/z.
    """
    if adduct_types is None:
        adduct_types = DEFAULT_ADDUCTS

    base_comp = Composition(sequence=sequence)
    result = {}
    for label in adduct_types:
        defn = ADDUCT_DEFINITIONS.get(label)
        if defn is not None:
            result[label] = round(compute_adduct_mz(base_comp, defn), 4)
    return result


def calculate_peptide_fragments(
    sequence: str,
    adduct_types: list[str] | None = None,
    abundance_threshold: float = 0.001,
) -> PeptideSpectrum:
    """Calculate theoretical b/y fragment ions and precursor isotopic envelope.

    Parameters
    ----------
    sequence : str
        Amino acid sequence (e.g. "PEPTIDE").
    adduct_types : list[str], optional
        Adduct labels for precursor isotopic envelopes. Default: ``DEFAULT_ADDUCTS``.
    abundance_threshold : float, optional
        Minimum relative abundance for isotopologues. Default: 0.001.

    Returns
    -------
    PeptideSpectrum
        Fragment ions and precursor isotopic envelopes.

    Raises
    ------
    ValueError
        If the sequence contains invalid amino acids.
    """
    if adduct_types is None:
        adduct_types = DEFAULT_ADDUCTS

    if not is_valid_peptide(sequence):
        raise ValueError(f"Invalid peptide sequence: '{sequence}'")

    n = len(sequence)
    fragments = []

    # Generate b and y ions (singly charged)
    for i in range(1, n):
        # b ion: N-terminal fragment
        b_mz = fast_mass(sequence[:i], ion_type="b", charge=1)
        fragments.append(PeptideFragment(
            label=f"b{i}", mz=round(b_mz, 4), ion_type="b", position=i
        ))

        # y ion: C-terminal fragment
        y_mz = fast_mass(sequence[n - i :], ion_type="y", charge=1)
        fragments.append(PeptideFragment(
            label=f"y{i}", mz=round(y_mz, 4), ion_type="y", position=i
        ))

    # Compute precursor isotopic envelopes (same pattern as calculate_theoretical_spectrum)
    base_comp = Composition(sequence=sequence)
    precursor_isotopes = {}

    for adduct_type in adduct_types:
        defn = ADDUCT_DEFINITIONS.get(adduct_type)
        if defn is None:
            continue

        try:
            adduct_comp = compute_adduct_composition(base_comp, defn)

            isos = list(
                isotopologues(
                    composition=adduct_comp,
                    report_abundance=True,
                    overall_threshold=abundance_threshold,
                )
            )

            if not isos:
                continue

            mz_list = []
            abundance_list = []
            for iso_comp, abundance in isos:
                mz_list.append(iso_comp.mass() / defn.charge)
                abundance_list.append(abundance)

            mz_array = np.array(mz_list)
            abundance_array = np.array(abundance_list)

            sort_idx = np.argsort(mz_array)
            mz_array = mz_array[sort_idx]
            abundance_array = abundance_array[sort_idx]

            max_abundance = abundance_array.max()
            if max_abundance > 0:
                abundance_array = abundance_array / max_abundance

            monoisotopic_mz = mz_array[0]

            precursor_isotopes[adduct_type] = AdductSpectrum(
                mz_values=mz_array,
                abundances=abundance_array,
                monoisotopic_mz=monoisotopic_mz,
            )

        except Exception as e:
            logger.warning(
                f"Failed to compute {adduct_type} isotopes for '{sequence}': {e}"
            )
            continue

    return PeptideSpectrum(
        sequence=sequence,
        fragments=fragments,
        precursor_isotopes=precursor_isotopes,
    )
