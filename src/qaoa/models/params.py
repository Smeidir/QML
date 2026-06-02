supported_qaoa_variants = ['vanilla', 'multiangle']
supported_param_inits = ['uniform','gaussian','static', 'interpolation']
supported_optimizers = [
    'Nelder-Mead', 'Powell', 'CG', 'BFGS', 'Newton-CG', 'L-BFGS-B', 'TNC', 
    'COBYLA', 'COBYQA', 'SLSQP', 'trust-constr', 'dogleg', 'trust-ncg', 
    'trust-exact', 'trust-krylov','SPSA'
]
supported_backends = ['statevector', 'noisy_sampling', 'quantum_backend']
CPUS_PER_WORKER = 4
db_path = 'qruns.db'
