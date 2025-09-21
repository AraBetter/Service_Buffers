"""
Global T_r (Recovery Time) Configuration Module
Provides a single source of truth for the recovery time value across all modules.
"""
import random

class TrConfig:
    """Singleton class to manage the global T_r value"""
    _instance = None
    _t_r = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TrConfig, cls).__new__(cls)
        return cls._instance
    
    def get_t_r(self):
        """Get the current T_r value in minutes"""
        if self._t_r is None:
            self._t_r = random.uniform(6, 600)  # 0.1 to 10 hours in minutes
        return self._t_r
    
    def set_t_r(self, value):
        """Set a specific T_r value in minutes"""
        self._t_r = value
    
    def reset_t_r(self):
        """Generate a new random T_r value"""
        self._t_r = random.uniform(6, 600)  # 0.1 to 10 hours in minutes
        return self._t_r

# Global instance
tr_config = TrConfig()

def get_global_t_r():
    """Get the global T_r value in minutes"""
    return tr_config.get_t_r()

def set_global_t_r(value):
    """Set the global T_r value in minutes"""
    tr_config.set_t_r(value)

def reset_global_t_r():
    """Reset and generate new T_r value"""
    return tr_config.reset_t_r()