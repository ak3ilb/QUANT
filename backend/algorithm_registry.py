"""
Source-aware registry for the algorithm modules used by the backend.

The registry separates literal mathematical implementations from market
heuristics inspired by the provided Simons/Renaissance references.
"""

ACADEMIC_REFERENCE = "academic_reference"
QUANT_MODEL = "quant_model"
PROJECT_HEURISTIC = "project_heuristic"


ALGORITHM_REGISTRY = [
    {
        "id": "chern_simons_gauge",
        "name": "Chern-Simons Gauge Heuristic",
        "category": ACADEMIC_REFERENCE,
        "module": "backend.algorithms.chern_simons",
        "implementation_status": "heuristic_analogy",
        "source_urls": [
            "https://en.wikipedia.org/wiki/Chern%E2%80%93Simons_form",
            "https://en.wikipedia.org/wiki/Chern%E2%80%93Simons_theory",
            "https://ncatlab.org/nlab/show/Chern-Simons+form",
        ],
        "caveat": (
            "The source material concerns Lie-algebra-valued connection 1-forms, "
            "curvature forms, wedge products, and topological field theory. This "
            "module uses return curvature proxies and is not a literal "
            "Chern-Simons form or Chern-Simons theory implementation."
        ),
    },
    {
        "id": "simons_hypersurface",
        "name": "Simons Formula Volatility Heuristic",
        "category": ACADEMIC_REFERENCE,
        "module": "backend.algorithms.simons_equation",
        "implementation_status": "heuristic_analogy",
        "source_urls": [
            "https://en.wikipedia.org/wiki/Simons%27_formula",
            "https://en.wikipedia.org/wiki/Simons_cone",
            "https://en.wikipedia.org/wiki/Bernstein%27s_problem",
        ],
        "caveat": (
            "Simons' formula is a differential-geometric identity for the "
            "Laplacian of the second fundamental form of a minimal submanifold. "
            "The code maps volatility derivatives to a market instability proxy; "
            "it does not model minimal hypersurfaces, the Simons cone, or "
            "Bernstein's problem."
        ),
    },
    {
        "id": "cheeger_simons_characters",
        "name": "Cheeger-Simons Cycle Heuristic",
        "category": ACADEMIC_REFERENCE,
        "module": "backend.algorithms.cheeger_simons",
        "implementation_status": "heuristic_analogy",
        "source_urls": [
            "https://ncatlab.org/nlab/show/Cheeger-Simons+differential+character",
        ],
        "caveat": (
            "Cheeger-Simons differential characters are differential cohomology "
            "objects assigning U(1) values to cycles with curvature constraints. "
            "The code computes a bounded price-cycle proxy only."
        ),
    },
    {
        "id": "hmm_baum_welch",
        "name": "Hidden Markov Regime Model",
        "category": QUANT_MODEL,
        "module": "backend.algorithms.hmm_baum_welch",
        "implementation_status": "implemented_model",
        "source_urls": [
            "https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund",
            "https://www.quantvps.com/blog/jim-simons-trading-strategy",
        ],
        "caveat": (
            "The sources support HMM/Baum-Welch as part of Renaissance history, "
            "but the real Medallion models are proprietary. This implementation "
            "is a local market-regime model over close-to-close returns."
        ),
    },
    {
        "id": "geometric_brownian_motion_sde",
        "name": "Geometric Brownian Motion Monte Carlo",
        "category": QUANT_MODEL,
        "module": "backend.algorithms.stochastic_diff_eq",
        "implementation_status": "implemented_model",
        "source_urls": [
            "https://www.quantvps.com/blog/jim-simons-trading-strategy",
        ],
        "caveat": (
            "The source references stochastic differential equations broadly. "
            "This code implements a GBM forecast, not an Ornstein-Uhlenbeck "
            "mean-reversion process and not a proprietary Renaissance model."
        ),
    },
    {
        "id": "kernel_regression",
        "name": "RBF Kernel Similarity Regression",
        "category": QUANT_MODEL,
        "module": "backend.algorithms.kernel_regression",
        "implementation_status": "implemented_model",
        "source_urls": [
            "https://www.quantvps.com/blog/jim-simons-trading-strategy",
            "https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund",
        ],
        "caveat": (
            "The implementation is a small RBF similarity model over recent "
            "returns, not a large-scale high-dimensional proprietary kernel "
            "research platform."
        ),
    },
    {
        "id": "berlekamp_massey",
        "name": "Berlekamp-Massey Sequence Heuristic",
        "category": QUANT_MODEL,
        "module": "backend.algorithms.berlekamp_massey",
        "implementation_status": "implemented_heuristic",
        "source_urls": [
            "https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund",
        ],
        "caveat": (
            "Elwyn Berlekamp is historically relevant to Medallion, but this "
            "module applies the Berlekamp-Massey linear recurrence algorithm to "
            "binary return signs as an experimental sequence proxy."
        ),
    },
    {
        "id": "kelly_sizing",
        "name": "Kelly Criterion Position Sizing",
        "category": QUANT_MODEL,
        "module": "backend.algorithms.kelly_criterion",
        "implementation_status": "implemented_heuristic",
        "source_urls": [
            "https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund",
        ],
        "caveat": (
            "The source supports Kelly-style sizing in the Renaissance story. "
            "This implementation uses a fixed 50.75% win-rate assumption and "
            "historical average win/loss ratio."
        ),
    },
    {
        "id": "medallion_signal",
        "name": "Project Medallion Signal Ensemble",
        "category": PROJECT_HEURISTIC,
        "module": "backend.signal_engine",
        "implementation_status": "project_specific",
        "source_urls": [
            "https://www.edgeful.com/blog/posts/jim-simons-trading-strategy-systematic-approach",
            "https://www.unicorngrowth.io/p/jim-simons-strategy",
            "https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund",
        ],
        "caveat": (
            "The sources describe systematic, data-driven, no-manual-override "
            "principles. This project signal is a transparent local ensemble, "
            "not a Renaissance Technologies or Medallion Fund implementation."
        ),
    },
]


def get_algorithm_registry() -> list[dict]:
    return [entry.copy() for entry in ALGORITHM_REGISTRY]
