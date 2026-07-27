"""
Enhanced blend optimization integrating regression analytics.

This module provides advanced crude oil blend optimization that incorporates
regression-based quality scores, processing indices, and enhanced valuations
alongside traditional cost minimization and quality constraints.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pyomo.environ import (
    ConcreteModel, Var, Objective, Constraint, NonNegativeReals, 
    minimize, maximize, value, SolverFactory, summation
)


class EnhancedBlendOptimizer:
    """
    Advanced crude blend optimizer with regression analytics integration.
    """
    
    def __init__(self, solver_name: str = "appsi_highs"):
        self.solver_name = solver_name
        self.model = None
        self.results = None
    
    def optimize_value_maximization(
        self,
        crude_analytics: pd.DataFrame,
        supply_limits: Dict[str, float],
        target_volume: float = 100000,
        use_enhanced_value: bool = True,
        quality_constraints: Optional[Dict] = None,
        processing_constraints: Optional[Dict] = None
    ) -> Dict:
        """
        Optimize crude blend to maximize total value using regression analytics.
        
        Args:
            crude_analytics: DataFrame with crude properties and regression predictions
            supply_limits: Maximum available volume for each crude
            target_volume: Target total blend volume
            use_enhanced_value: Use enhanced_gross_value vs netback_usd_bbl
            quality_constraints: Quality requirements (min_api, max_sulfur, min_quality_score)
            processing_constraints: Processing limits (max_processing_index, min_refinery_margin)
        
        Returns:
            Optimization results dictionary
        """
        
        # Validate inputs
        required_cols = ['crude_id', 'api', 'sulfur_wt']
        if use_enhanced_value:
            required_cols.extend(['enhanced_gross_value', 'quality_score', 'processing_index', 'refinery_margin'])
        else:
            required_cols.append('netback_usd_bbl')
        
        missing_cols = [col for col in required_cols if col not in crude_analytics.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Set up optimization model
        self.model = ConcreteModel()
        crudes = list(crude_analytics['crude_id'])
        self.model.CRUDES = crudes
        
        # Decision variables: volume of each crude
        self.model.x = Var(crudes, domain=NonNegativeReals)
        
        # Objective: maximize total value
        value_col = 'enhanced_gross_value' if use_enhanced_value else 'netback_usd_bbl'
        
        def objective_rule():
            return sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c][value_col].iloc[0])
                      for c in crudes)
        
        self.model.obj = Objective(rule=objective_rule, sense=maximize)
        
        # Volume constraint: meet target volume exactly
        self.model.volume_constraint = Constraint(
            expr=sum(self.model.x[c] for c in crudes) == target_volume
        )
        
        # Supply constraints
        for c in crudes:
            max_supply = supply_limits.get(c, 0)
            self.model.add_component(
                f"supply_{c}",
                Constraint(expr=self.model.x[c] <= max_supply)
            )
        
        # Quality constraints
        if quality_constraints:
            self._add_quality_constraints(crude_analytics, quality_constraints, target_volume)
        
        # Processing constraints
        if processing_constraints and use_enhanced_value:
            self._add_processing_constraints(crude_analytics, processing_constraints, target_volume)
        
        # Solve the optimization
        solver = SolverFactory(self.solver_name)
        self.results = solver.solve(self.model, tee=False)
        
        # Extract and return results
        return self._extract_results(crude_analytics, target_volume, use_enhanced_value)
    
    def optimize_cost_minimization(
        self,
        crude_analytics: pd.DataFrame,
        crude_costs: Dict[str, float],
        target_volume: float = 100000,
        quality_constraints: Optional[Dict] = None,
        processing_constraints: Optional[Dict] = None
    ) -> Dict:
        """
        Optimize crude blend to minimize total cost while meeting constraints.
        
        Args:
            crude_analytics: DataFrame with crude properties and regression predictions
            crude_costs: Cost per barrel for each crude
            target_volume: Target total blend volume
            quality_constraints: Quality requirements
            processing_constraints: Processing limits
            
        Returns:
            Optimization results dictionary
        """
        
        # Set up optimization model
        self.model = ConcreteModel()
        crudes = list(crude_analytics['crude_id'])
        self.model.CRUDES = crudes
        
        # Decision variables
        self.model.x = Var(crudes, domain=NonNegativeReals)
        
        # Objective: minimize total cost
        def objective_rule():
            return sum(self.model.x[c] * crude_costs.get(c, 0) for c in crudes)
        
        self.model.obj = Objective(rule=objective_rule, sense=minimize)
        
        # Volume constraint
        self.model.volume_constraint = Constraint(
            expr=sum(self.model.x[c] for c in crudes) == target_volume
        )
        
        # Quality constraints (required for cost minimization)
        if quality_constraints:
            self._add_quality_constraints(crude_analytics, quality_constraints, target_volume)
        
        # Processing constraints
        if processing_constraints:
            self._add_processing_constraints(crude_analytics, processing_constraints, target_volume)
        
        # Solve the optimization
        solver = SolverFactory(self.solver_name)
        self.results = solver.solve(self.model, tee=False)
        
        # Extract results
        return self._extract_results(crude_analytics, target_volume, use_enhanced_value=False, 
                                   crude_costs=crude_costs)
    
    def _add_quality_constraints(self, crude_analytics: pd.DataFrame, 
                               quality_constraints: Dict, target_volume: float):
        """Add quality constraints to the optimization model."""
        
        crudes = self.model.CRUDES
        
        # API gravity constraints
        if 'min_api' in quality_constraints:
            self.model.min_api_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['api'].iloc[0])
                        for c in crudes) >= quality_constraints['min_api'] * target_volume
            )
        
        if 'max_api' in quality_constraints:
            self.model.max_api_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['api'].iloc[0])
                        for c in crudes) <= quality_constraints['max_api'] * target_volume
            )
        
        # Sulfur content constraints
        if 'max_sulfur' in quality_constraints:
            self.model.max_sulfur_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['sulfur_wt'].iloc[0])
                        for c in crudes) <= quality_constraints['max_sulfur'] * target_volume
            )
        
        if 'min_sulfur' in quality_constraints:
            self.model.min_sulfur_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['sulfur_wt'].iloc[0])
                        for c in crudes) >= quality_constraints['min_sulfur'] * target_volume
            )
        
        # Distillation cut constraints
        for cut_type in ['cut_light_pct', 'cut_middle_pct', 'cut_heavy_pct']:
            if f'min_{cut_type}' in quality_constraints and cut_type in crude_analytics.columns:
                constraint_name = f'min_{cut_type}_constraint'
                self.model.add_component(constraint_name, Constraint(
                    expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c][cut_type].iloc[0])
                            for c in crudes) >= quality_constraints[f'min_{cut_type}'] * target_volume
                ))
            
            if f'max_{cut_type}' in quality_constraints and cut_type in crude_analytics.columns:
                constraint_name = f'max_{cut_type}_constraint'
                self.model.add_component(constraint_name, Constraint(
                    expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c][cut_type].iloc[0])
                            for c in crudes) <= quality_constraints[f'max_{cut_type}'] * target_volume
                ))
        
        # Quality score constraint (regression-based)
        if 'min_quality_score' in quality_constraints and 'quality_score' in crude_analytics.columns:
            self.model.min_quality_score_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['quality_score'].iloc[0])
                        for c in crudes) >= quality_constraints['min_quality_score'] * target_volume
            )
    
    def _add_processing_constraints(self, crude_analytics: pd.DataFrame,
                                  processing_constraints: Dict, target_volume: float):
        """Add processing constraints to the optimization model."""
        
        crudes = self.model.CRUDES
        
        # Maximum processing complexity index
        if 'max_processing_index' in processing_constraints and 'processing_index' in crude_analytics.columns:
            self.model.max_processing_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['processing_index'].iloc[0])
                        for c in crudes) <= processing_constraints['max_processing_index'] * target_volume
            )
        
        # Minimum refinery margin
        if 'min_refinery_margin' in processing_constraints and 'refinery_margin' in crude_analytics.columns:
            self.model.min_refinery_margin_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['refinery_margin'].iloc[0])
                        for c in crudes) >= processing_constraints['min_refinery_margin'] * target_volume
            )
        
        # Maximum refinery margin (for cost control)
        if 'max_refinery_margin' in processing_constraints and 'refinery_margin' in crude_analytics.columns:
            self.model.max_refinery_margin_constraint = Constraint(
                expr=sum(self.model.x[c] * float(crude_analytics[crude_analytics['crude_id'] == c]['refinery_margin'].iloc[0])
                        for c in crudes) <= processing_constraints['max_refinery_margin'] * target_volume
            )
    
    def _extract_results(self, crude_analytics: pd.DataFrame, target_volume: float,
                        use_enhanced_value: bool, crude_costs: Optional[Dict] = None) -> Dict:
        """Extract optimization results."""
        
        from pyomo.opt import TerminationCondition
        
        if not hasattr(self.results.solver, 'termination_condition'):
            status = 'unknown'
        elif self.results.solver.termination_condition == TerminationCondition.optimal:
            status = 'optimal'
        elif self.results.solver.termination_condition == TerminationCondition.infeasible:
            status = 'infeasible'
        else:
            status = str(self.results.solver.termination_condition)
        
        if status != 'optimal':
            return {
                'status': status,
                'message': 'Optimization failed',
                'total_value': 0,
                'total_volume': 0,
                'blend_composition': {},
                'blend_properties': {}
            }
        
        # Extract solution
        solution = {}
        total_value = 0
        total_cost = 0
        total_volume = 0
        
        # Weighted property totals
        weighted_api = 0
        weighted_sulfur = 0
        weighted_quality_score = 0
        weighted_processing_index = 0
        weighted_refinery_margin = 0
        weighted_light_cuts = 0
        weighted_middle_cuts = 0
        weighted_heavy_cuts = 0
        
        value_col = 'enhanced_gross_value' if use_enhanced_value else 'netback_usd_bbl'
        
        for c in self.model.CRUDES:
            volume = value(self.model.x[c])
            
            if volume > 0.01:  # Only include significant volumes
                crude_info = crude_analytics[crude_analytics['crude_id'] == c].iloc[0]
                
                crude_value = float(crude_info[value_col]) if value_col in crude_info else 0
                crude_cost = crude_costs.get(c, 0) if crude_costs else 0
                
                solution[c] = {
                    'volume': volume,
                    'percentage': (volume / target_volume) * 100,
                    'value_per_barrel': crude_value,
                    'cost_per_barrel': crude_cost,
                    'api': float(crude_info['api']),
                    'sulfur_wt': float(crude_info['sulfur_wt']),
                    'cut_light_pct': float(crude_info.get('cut_light_pct', 0)),
                    'cut_middle_pct': float(crude_info.get('cut_middle_pct', 0)),
                    'cut_heavy_pct': float(crude_info.get('cut_heavy_pct', 0))
                }
                
                # Add regression metrics if available
                if 'quality_score' in crude_info:
                    solution[c]['quality_score'] = float(crude_info['quality_score'])
                if 'processing_index' in crude_info:
                    solution[c]['processing_index'] = float(crude_info['processing_index'])
                if 'refinery_margin' in crude_info:
                    solution[c]['refinery_margin'] = float(crude_info['refinery_margin'])
                
                # Accumulate weighted totals
                total_value += volume * crude_value
                total_cost += volume * crude_cost
                total_volume += volume
                
                weighted_api += volume * float(crude_info['api'])
                weighted_sulfur += volume * float(crude_info['sulfur_wt'])
                weighted_light_cuts += volume * float(crude_info.get('cut_light_pct', 0))
                weighted_middle_cuts += volume * float(crude_info.get('cut_middle_pct', 0))
                weighted_heavy_cuts += volume * float(crude_info.get('cut_heavy_pct', 0))
                
                if 'quality_score' in crude_info:
                    weighted_quality_score += volume * float(crude_info['quality_score'])
                if 'processing_index' in crude_info:
                    weighted_processing_index += volume * float(crude_info['processing_index'])
                if 'refinery_margin' in crude_info:
                    weighted_refinery_margin += volume * float(crude_info['refinery_margin'])
        
        # Calculate blended properties
        blend_properties = {}
        if total_volume > 0:
            blend_properties = {
                'blended_api': weighted_api / total_volume,
                'blended_sulfur_wt': weighted_sulfur / total_volume,
                'blended_light_cuts': weighted_light_cuts / total_volume,
                'blended_middle_cuts': weighted_middle_cuts / total_volume,
                'blended_heavy_cuts': weighted_heavy_cuts / total_volume
            }
            
            if weighted_quality_score > 0:
                blend_properties['blended_quality_score'] = weighted_quality_score / total_volume
            if weighted_processing_index > 0:
                blend_properties['blended_processing_index'] = weighted_processing_index / total_volume
            if weighted_refinery_margin > 0:
                blend_properties['blended_refinery_margin'] = weighted_refinery_margin / total_volume
        
        return {
            'status': status,
            'optimization_type': 'Enhanced Value Maximization' if use_enhanced_value else 'Cost Minimization',
            'total_value': total_value,
            'total_cost': total_cost,
            'total_volume': total_volume,
            'avg_value_per_barrel': total_value / total_volume if total_volume > 0 else 0,
            'avg_cost_per_barrel': total_cost / total_volume if total_volume > 0 else 0,
            'blend_composition': solution,
            'blend_properties': blend_properties,
            'objective_value': value(self.model.obj) if self.model else 0
        }


def compare_optimization_strategies(
    crude_analytics: pd.DataFrame,
    supply_limits: Dict[str, float],
    crude_costs: Dict[str, float],
    target_volume: float = 100000,
    quality_constraints: Optional[Dict] = None,
    processing_constraints: Optional[Dict] = None
) -> Dict:
    """
    Compare different optimization strategies side by side.
    
    Returns:
        Dictionary with results from multiple optimization approaches
    """
    
    optimizer = EnhancedBlendOptimizer()
    results = {}
    
    # Strategy 1: Traditional netback maximization
    try:
        results['traditional_value_max'] = optimizer.optimize_value_maximization(
            crude_analytics, supply_limits, target_volume, 
            use_enhanced_value=False, quality_constraints=quality_constraints
        )
    except Exception as e:
        results['traditional_value_max'] = {'status': 'failed', 'error': str(e)}
    
    # Strategy 2: Enhanced value maximization with regression
    try:
        results['enhanced_value_max'] = optimizer.optimize_value_maximization(
            crude_analytics, supply_limits, target_volume,
            use_enhanced_value=True, quality_constraints=quality_constraints,
            processing_constraints=processing_constraints
        )
    except Exception as e:
        results['enhanced_value_max'] = {'status': 'failed', 'error': str(e)}
    
    # Strategy 3: Cost minimization with quality constraints
    try:
        results['cost_minimization'] = optimizer.optimize_cost_minimization(
            crude_analytics, crude_costs, target_volume,
            quality_constraints=quality_constraints,
            processing_constraints=processing_constraints
        )
    except Exception as e:
        results['cost_minimization'] = {'status': 'failed', 'error': str(e)}
    
    return results
