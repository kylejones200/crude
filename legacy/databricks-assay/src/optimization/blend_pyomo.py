from typing import Dict, Tuple
import pandas as pd
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, NonNegativeReals, minimize, value, SolverFactory


def optimize_blend(
    supply_df: pd.DataFrame,
    assays_df: pd.DataFrame,
    target_volume_bbl: float,
    min_api: float,
    max_sulfur_wt: float,
    solver: str = "appsi_highs",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Linear blending optimization: minimize total cost while meeting volume and quality specs.

    Inputs
    ------
    supply_df: columns [crude_id, cost_usd_bbl, available_bbl]
    assays_df: columns [crude_id, api, sulfur_wt]

    Returns
    -------
    (blend_df, metrics)
    blend_df: columns [crude_id, vol_bbl, cost_usd_bbl]
    metrics: dict with total_cost, blended_api, blended_sulfur, total_vol
    """
    df = (supply_df.merge(assays_df[["crude_id", "api", "sulfur_wt"]], on="crude_id", how="inner").copy())
    crudes = df["crude_id"].tolist()

    m = ConcreteModel()

    # Decision variables: volume of each crude to take
    m.vol = Var(crudes, domain=NonNegativeReals)

    # Objective: minimize total cost
    m.obj = Objective(expr=sum(m.vol[i] * float(df.loc[df.crude_id == i, "cost_usd_bbl"].iloc[0]) for i in crudes), sense=minimize)

    # Volume constraint
    m.total_vol = Constraint(expr=sum(m.vol[i] for i in crudes) == float(target_volume_bbl))

    # Availability constraints
    m.availability = ConstraintListLike()
    for i in crudes:
        avail = float(df.loc[df.crude_id == i, "available_bbl"].iloc[0])
        m.add_component(f"avail_{i}", Constraint(expr=m.vol[i] <= avail))

    # API spec: weighted average >= min_api
    api_terms = [m.vol[i] * float(df.loc[df.crude_id == i, "api"].iloc[0]) for i in crudes]
    m.api_spec = Constraint(expr=sum(api_terms) >= min_api * target_volume_bbl)

    # Sulfur spec: weighted average <= max_sulfur
    s_terms = [m.vol[i] * float(df.loc[df.crude_id == i, "sulfur_wt"].iloc[0]) for i in crudes]
    m.sulfur_spec = Constraint(expr=sum(s_terms) <= max_sulfur_wt * target_volume_bbl)

    # Solve
    opt = SolverFactory(solver)
    results = opt.solve(m, tee=False)

    # Collect results
    vols = {i: value(m.vol[i]) for i in crudes}
    out_rows = []
    for i in crudes:
        out_rows.append({
            "crude_id": i,
            "vol_bbl": vols[i],
            "cost_usd_bbl": float(df.loc[df.crude_id == i, "cost_usd_bbl"].iloc[0]),
        })
    blend_df = pd.DataFrame(out_rows)

    total_vol = blend_df["vol_bbl"].sum()
    total_cost = (blend_df["vol_bbl"] * blend_df["cost_usd_bbl"]).sum()

    # Blended qualities
    merged = blend_df.merge(df[["crude_id", "api", "sulfur_wt"]], on="crude_id", how="left")
    blended_api = (merged["vol_bbl"] * merged["api"]).sum() / total_vol if total_vol > 0 else 0.0
    blended_s = (merged["vol_bbl"] * merged["sulfur_wt"]).sum() / total_vol if total_vol > 0 else 0.0

    metrics = {
        "total_cost_usd": total_cost,
        "total_vol_bbl": total_vol,
        "blended_api": blended_api,
        "blended_sulfur_wt": blended_s,
        "solver_status": str(results.solver.status),
        "termination_condition": str(results.solver.termination_condition),
    }

    return blend_df, metrics


# Minimal ConstraintList stand-in without importing from pyomo.core directly in Databricks runtime
from pyomo.core import ConstraintList as _ConstraintList
class ConstraintListLike(_ConstraintList):
    pass
