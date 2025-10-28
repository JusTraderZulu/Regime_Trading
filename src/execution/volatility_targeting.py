"""
Volatility Targeting Allocation

Implements covariance-aware portfolio allocation with volatility targeting,
per-leg floors/ceilings, and comprehensive diagnostics.

Features:
- Target portfolio volatility
- Covariance-aware scaling
- Per-position constraints (min/max weights)
- Robust covariance estimation
- Diagnostic outputs for monitoring
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VolatilityTargetConfig:
    """Configuration for volatility targeting"""
    target_volatility: float = 0.15      # Target portfolio volatility (15% annualized)
    lookback_days: int = 30              # Days for covariance estimation
    min_observations: int = 20           # Minimum bars required
    min_weight: float = 0.0              # Minimum position weight
    max_weight: float = 0.25             # Maximum position weight (25% per leg)
    use_shrinkage: bool = True           # Ledoit-Wolf shrinkage for covariance
    annualization_factor: float = 252.0  # Trading days per year
    

@dataclass
class AllocationDiagnostics:
    """Diagnostic information from allocation"""
    original_weights: Dict[str, float]
    scaled_weights: Dict[str, float]
    estimated_volatility: float
    target_volatility: float
    scaling_factor: float
    covariance_condition_number: float
    observations_used: int
    warnings: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'original_weights': self.original_weights,
            'scaled_weights': self.scaled_weights,
            'estimated_volatility': self.estimated_volatility,
            'target_volatility': self.target_volatility,
            'scaling_factor': self.scaling_factor,
            'covariance_condition_number': self.covariance_condition_number,
            'observations_used': self.observations_used,
            'warnings': self.warnings
        }


class VolatilityTargetAllocator:
    """
    Covariance-aware portfolio allocator with volatility targeting.
    
    Scales signal weights to achieve a target portfolio volatility while
    respecting per-position constraints.
    
    Example:
        config = VolatilityTargetConfig(target_volatility=0.15, max_weight=0.25)
        allocator = VolatilityTargetAllocator(config)
        
        # Get recent returns for all assets
        returns_dict = {'SPY': spy_returns, 'X:BTCUSD': btc_returns}
        
        # Original signal weights
        signal_weights = {'SPY': 0.5, 'X:BTCUSD': 0.3}
        
        # Scale to target volatility
        scaled_weights, diagnostics = allocator.allocate(signal_weights, returns_dict)
    """
    
    def __init__(self, config: VolatilityTargetConfig):
        """
        Initialize allocator with configuration.
        
        Args:
            config: VolatilityTargetConfig with target vol and constraints
        """
        self.config = config
        logger.info(
            f"VolatilityTargetAllocator initialized "
            f"(target_vol={config.target_volatility:.1%}, "
            f"lookback={config.lookback_days}d)"
        )
    
    def allocate(
        self,
        signal_weights: Dict[str, float],
        returns_data: Dict[str, pd.Series]
    ) -> Tuple[Dict[str, float], AllocationDiagnostics]:
        """
        Scale signal weights to achieve target portfolio volatility.
        
        Args:
            signal_weights: Original signal weights (e.g., {'SPY': 0.5, 'BTC': 0.3})
            returns_data: Recent returns for each asset (pd.Series)
            
        Returns:
            Tuple of (scaled_weights, diagnostics)
        """
        warnings = []
        
        # Validate inputs
        if not signal_weights:
            logger.warning("No signal weights provided")
            return {}, AllocationDiagnostics(
                original_weights={},
                scaled_weights={},
                estimated_volatility=0.0,
                target_volatility=self.config.target_volatility,
                scaling_factor=0.0,
                covariance_condition_number=0.0,
                observations_used=0,
                warnings=["No signal weights provided"]
            )
        
        # Filter to assets with both weights and returns
        valid_assets = [
            asset for asset in signal_weights.keys()
            if asset in returns_data and returns_data[asset] is not None
        ]
        
        if not valid_assets:
            warnings.append("No valid assets with both signals and returns")
            logger.warning("No valid assets for allocation")
            return signal_weights, AllocationDiagnostics(
                original_weights=signal_weights.copy(),
                scaled_weights=signal_weights.copy(),
                estimated_volatility=0.0,
                target_volatility=self.config.target_volatility,
                scaling_factor=1.0,
                covariance_condition_number=0.0,
                observations_used=0,
                warnings=warnings
            )
        
        # Build returns matrix
        returns_df, obs_count = self._build_returns_matrix(returns_data, valid_assets)
        
        if returns_df is None or obs_count < self.config.min_observations:
            warnings.append(
                f"Insufficient observations ({obs_count} < {self.config.min_observations})"
            )
            logger.warning(f"Insufficient data for covariance estimation: {obs_count} obs")
            return signal_weights, AllocationDiagnostics(
                original_weights=signal_weights.copy(),
                scaled_weights=signal_weights.copy(),
                estimated_volatility=0.0,
                target_volatility=self.config.target_volatility,
                scaling_factor=1.0,
                covariance_condition_number=0.0,
                observations_used=obs_count,
                warnings=warnings
            )
        
        # Estimate covariance matrix
        cov_matrix, cond_number = self._estimate_covariance(returns_df)
        
        if cov_matrix is None:
            warnings.append("Covariance estimation failed (degenerate matrix)")
            logger.error("Failed to estimate covariance matrix")
            return signal_weights, AllocationDiagnostics(
                original_weights=signal_weights.copy(),
                scaled_weights=signal_weights.copy(),
                estimated_volatility=0.0,
                target_volatility=self.config.target_volatility,
                scaling_factor=1.0,
                covariance_condition_number=float('inf'),
                observations_used=obs_count,
                warnings=warnings
            )
        
        # Build weight vector (in same order as covariance matrix)
        weight_vector = np.array([signal_weights.get(asset, 0.0) for asset in valid_assets])
        
        # Calculate portfolio volatility with current weights
        portfolio_variance = weight_vector @ cov_matrix @ weight_vector
        portfolio_vol = np.sqrt(portfolio_variance * self.config.annualization_factor)
        
        # Calculate scaling factor to hit target volatility
        if portfolio_vol > 0:
            scaling_factor = self.config.target_volatility / portfolio_vol
        else:
            scaling_factor = 1.0
            warnings.append("Zero portfolio volatility, no scaling applied")
        
        # Scale weights
        scaled_weights_raw = {
            asset: signal_weights.get(asset, 0.0) * scaling_factor
            for asset in valid_assets
        }
        
        # Apply per-leg constraints (floor/ceiling)
        scaled_weights_final = {}
        for asset, weight in scaled_weights_raw.items():
            clamped_weight = np.clip(
                weight,
                self.config.min_weight,
                self.config.max_weight
            )
            
            if clamped_weight != weight:
                warnings.append(
                    f"{asset}: weight clamped {weight:.3f} → {clamped_weight:.3f}"
                )
            
            scaled_weights_final[asset] = clamped_weight
        
        # Include zero-weight assets from original signals
        for asset in signal_weights.keys():
            if asset not in scaled_weights_final:
                scaled_weights_final[asset] = 0.0
        
        # Create diagnostics
        diagnostics = AllocationDiagnostics(
            original_weights=signal_weights.copy(),
            scaled_weights=scaled_weights_final,
            estimated_volatility=portfolio_vol,
            target_volatility=self.config.target_volatility,
            scaling_factor=scaling_factor,
            covariance_condition_number=cond_number,
            observations_used=obs_count,
            warnings=warnings
        )
        
        logger.info(
            f"Volatility targeting: {portfolio_vol:.1%} → {self.config.target_volatility:.1%} "
            f"(scale={scaling_factor:.2f}, cond={cond_number:.1e})"
        )
        
        return scaled_weights_final, diagnostics
    
    def _build_returns_matrix(
        self,
        returns_data: Dict[str, pd.Series],
        valid_assets: List[str]
    ) -> Tuple[Optional[pd.DataFrame], int]:
        """
        Build aligned returns matrix from individual series.
        
        Args:
            returns_data: Dict of asset -> returns Series
            valid_assets: List of assets to include
            
        Returns:
            Tuple of (DataFrame with aligned returns, observation count)
        """
        try:
            # Align all series to common index
            series_list = []
            for asset in valid_assets:
                returns = returns_data[asset]
                if returns is not None and len(returns) > 0:
                    series_list.append(returns.rename(asset))
            
            if not series_list:
                return None, 0
            
            # Concatenate and align
            returns_df = pd.concat(series_list, axis=1)
            
            # Drop rows with any NaN
            returns_df = returns_df.dropna()
            
            # Limit to lookback window
            if len(returns_df) > self.config.lookback_days:
                returns_df = returns_df.iloc[-self.config.lookback_days:]
            
            return returns_df, len(returns_df)
            
        except Exception as e:
            logger.error(f"Failed to build returns matrix: {e}")
            return None, 0
    
    def _estimate_covariance(
        self,
        returns_df: pd.DataFrame
    ) -> Tuple[Optional[np.ndarray], float]:
        """
        Estimate covariance matrix with optional shrinkage.
        
        Args:
            returns_df: DataFrame of returns (assets as columns)
            
        Returns:
            Tuple of (covariance matrix, condition number)
        """
        try:
            if self.config.use_shrinkage:
                # Ledoit-Wolf shrinkage for better estimation
                cov_matrix = self._ledoit_wolf_shrinkage(returns_df)
            else:
                # Sample covariance
                cov_matrix = returns_df.cov().values
            
            # Calculate condition number (stability metric)
            cond_number = np.linalg.cond(cov_matrix)
            
            if cond_number > 1e10:
                logger.warning(f"Covariance matrix poorly conditioned: {cond_number:.1e}")
            
            return cov_matrix, cond_number
            
        except Exception as e:
            logger.error(f"Covariance estimation failed: {e}")
            return None, float('inf')
    
    def _ledoit_wolf_shrinkage(self, returns_df: pd.DataFrame) -> np.ndarray:
        """
        Apply Ledoit-Wolf shrinkage to covariance matrix.
        
        Shrinks sample covariance toward diagonal matrix for stability.
        
        Args:
            returns_df: DataFrame of returns
            
        Returns:
            Shrunk covariance matrix
        """
        from sklearn.covariance import LedoitWolf
        
        try:
            lw = LedoitWolf()
            lw.fit(returns_df.values)
            return lw.covariance_
        except Exception as e:
            logger.warning(f"Ledoit-Wolf failed, using sample covariance: {e}")
            return returns_df.cov().values


def apply_volatility_targeting(
    signal_weights: Dict[str, float],
    returns_data: Dict[str, pd.Series],
    config: VolatilityTargetConfig
) -> Tuple[Dict[str, float], AllocationDiagnostics]:
    """
    Convenience function for volatility targeting.
    
    Args:
        signal_weights: Original signal weights
        returns_data: Recent returns for each asset
        config: Volatility targeting configuration
        
    Returns:
        Tuple of (scaled weights, diagnostics)
    """
    allocator = VolatilityTargetAllocator(config)
    return allocator.allocate(signal_weights, returns_data)

