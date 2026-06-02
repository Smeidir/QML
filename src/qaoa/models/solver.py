from docplex.mp.model import Model
from matplotlib import pyplot as plt
import rustworkx as rx
import numpy as np
from qiskit_optimization.translators import from_docplex_mp

from abc import ABC, abstractmethod

def create_solver(graph, problem_type, **kwargs):
    match problem_type.lower():
        case 'maxcut':
            return MaxCutSolver(graph, problem_type,  **kwargs)
        case 'minvertexcover':
            return MinVertexCoverSolver(graph,problem_type, **kwargs)
        case _:
            raise ValueError(f"Unknown problem type: {problem_type}")

class Solver(ABC):
    """
    Class which contains the ordinary cplex solver.
    Used for getting solutions to compare with quantum solution.
    Needs graph, and what optimization problem it should solve - currently either maxcut or minvertexcover.
    """
    
    def __init__(self, graph, problem_type: str, verbose = False, lagrangian = 2):

        """
        Initializes the model with the given problem, but does not solve.
        Vertexcover is a boolean flag for if the problem is vertexcover, else it is maxcut.
        Lagrangian decides how to weight the constraints, if any."""

        self.graph = graph
        self.problem_type = problem_type
        self.verbose = verbose
        self.lagrangian = lagrangian
                

    def plot_result(self, bitstring=None):
        """
        Plots graph of partition. If no bitstring is supplied, must be run after solve.
        """
        if not bitstring:
            bitstring = [int(var.solution_value) for var in self.variables]

        colors = ["tab:grey" if i == 0 else "tab:purple" for i in bitstring]
        pos, default_axes = rx.spring_layout(self.graph), plt.axes(frameon=True)
        rx.visualization.mpl_draw(self.graph, node_color=colors, node_size=100, alpha=0.8, pos=pos) 


    def __str__(self):
        return f"{self.__class__.__name__} on graph with {len(self.graph)} nodes"

    @abstractmethod
    def evaluate_bitstring(self, bitstring):
        pass

    @abstractmethod
    def build_model(self):
        pass

    def get_qp(self): #TODO: check if this works without explicitly creating the problem unconstrained
        """ Return a quadratic program using : from qiskit_optimization.translators import from_docplex_mp"""
        return from_docplex_mp(self.model) 
    
    @abstractmethod
    def solve(self):
        pass
    
    @abstractmethod
    def solve_relaxed(self, method):
        pass



class MaxCutSolver(Solver):

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.build_model()
        
    def build_model(self):

        self.model = Model(name="MaxCut")

        self.variables = self.model.binary_var_list(len(self.graph), name='x')
        
        objective = 0

        try:

            for (i,j, w) in self.graph.weighted_edge_list():            
                objective+= w*(self.variables[i] + self.variables[j] - 2*self.variables[i]*self.variables[j]) 
        except AttributeError or TypeError: 
            for (i,j) in self.graph.edge_list():            
                objective+= (self.variables[i] + self.variables[j] - 2*self.variables[i]*self.variables[j]) 

        self.objective = objective
        self.model.objective=objective
        self.model.maximize(self.objective)
            
    def evaluate_bitstring(self, bitstring, mark_infeasible = False):
        """
        Evaluates the objective value for a given bitstring.
        Does so based on what type of problem the solves is initialized for. 
        Mark infeasible is for better plotting of solutions.
        """
        objective_value = 0
        try: 
            for (i, j, w) in self.graph.weighted_edge_list():
                objective_value += w * (bitstring[i] + bitstring[j] - 2 * bitstring[i] * bitstring[j])
        except TypeError:
            for (i, j) in self.graph.edge_list():
                objective_value += (bitstring[i] + bitstring[j] - 2 * bitstring[i] * bitstring[j])
                
        return objective_value
    


    
    def solve(self):
        """
        Solves the problem as it is initialized in the solver.
        Returns bitstring, solution_value
        """
        if self.verbose:
            print(f'Objective to maximize: {self.objective}')


        solution = self.model.solve()
        bitstring = [var.solution_value for var in self.variables]
        if self.verbose:
            print(solution.get_objective_value(), bitstring)
        return bitstring, solution.get_objective_value()
    
    
    def solve_relaxed(self, method = 'GW'):
        """ Solves the relaxed version of a problem, where the X values are continous between 0 and 1. 
        Method keyword is for future use with different relaxed solving methods. Default is Goemanns-Williamson."""

        raise ValueError('Not implemented yet')


    def get_feasible_solutions_hamming(self):
        return None


class MinVertexCoverSolver(Solver):

    """WARNING: MUST BE A WEIGHTED GRAPH!
    If not, we will have bugs with the weights - an unweighted graph will be weighted by index."""
        
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.build_model()
    
    def build_model(self):

        self.model = Model(name="VertexCover")
        self.variables = self.model.binary_var_list(len(self.graph), name='x')

        objective = 0

        #for edge in graph.edges:
        self.B = 1

        for i,var in enumerate(self.variables):
            objective += self.B*var*self.graph[i]

        for (i,j) in self.graph.edge_list(): #This is quadratic on purpose to make it align with a QUBO. Can be done linearly 
            objective += self.lagrangian*(1- self.variables[i])*( 1-self.variables[j])

        self.objective = objective
        self.model.objective=objective
        self.model.minimize(self.objective)

    def evaluate_bitstring(self, bitstring, mark_infeasible = False):
        """
        Evaluates the objective value for a given bitstring.
        Does so based on what type of problem the solves is initialized for. 
        Mark infeasible is for better plotting of solutions. If mark_infeasible = True, will return
        a tuple where the 0-th index is the objective value with violation penalty, and the 
        1-index is boolean where True indicates infeasible solution.
        """
        is_infeasible = 0
        obj_value = self.B*sum([bitstring[i]*self.graph[i] for i in range(len(bitstring))])

        for (i, j) in self.graph.edge_list():
            is_infeasible += self.lagrangian*(1 - bitstring[i]) * (1 - bitstring[j])
        if is_infeasible:  #TODO dobbeltsjekk når denne blir kalt
            if mark_infeasible:
                return (obj_value + is_infeasible, True) #now returns value + violation
            else:
                return obj_value + is_infeasible
        if mark_infeasible:
            return (obj_value, False)
        return obj_value

    def solve(self):
        """
        Solves the problem as it is initialized in the solver.
        Returns bitstring, solution_value
        """

        if self.verbose:
            print(f'Objective to minimize: {self.objective}')
            
        m = Model(name="vc_exact")
        x = m.binary_var_list(len(self.graph), name="x")
        # cover constraints
        for i,j in self.graph.edge_list():
            m.add_constraint(x[i] + x[j] >= 1)
        # pure size objective
        m.minimize(m.sum(x[i]*self.graph[i] for i in range(len(self.graph))))
        # Solve the model
        solution = m.solve()
        self.variables = x
        # Extract the solution
        bitstring = [x[i].solution_value for i in range(len(self.graph))]
        
        if self.verbose:
            print(solution.get_objective_value(), bitstring)
            
        return bitstring, solution.get_objective_value()

    def get_feasible_solutions_hamming(self):
        """
        Returns all feasible solutions to the Minimum Vertex Cover problem.
        A solution is feasible if every edge has at least one of its endpoints in the cover.
        Not optimized at all.

        Returns:
            dict: A list of all feasible bitstrings (vertex covers), sorted by hamming distance from the best one.
        """
        n = len(self.graph)
        feasible_solutions = {}
        # Generate all possible bitstrings
        for i in range(2**n):
            # Convert integer to binary representation (bitstring)
            bitstring = [(i >> j) & 1 for j in range(n)]
            
            # Check if this is a valid vertex cover
            is_valid = True
            for u, v in self.graph.edge_list():
                if bitstring[u] == 0 and bitstring[v] == 0:
                    is_valid = False
                    break
            if is_valid:
                try:
                    feasible_solutions[self.evaluate_bitstring(bitstring)].append(bitstring)
                    
                except KeyError:
                    feasible_solutions[self.evaluate_bitstring(bitstring)] = [bitstring]
        best_solution = feasible_solutions[min(feasible_solutions.keys())]
        hamming_dict = {x: [] for x in range(n+1)}
        for current_solution in feasible_solutions.values():
            hamming_dict[np.count_nonzero(np.array(best_solution)!=np.array(current_solution))].append(current_solution[0])



                    
        return hamming_dict

    def solve_relaxed(self, method = 'GW'):
        """ Solves the relaxed version of a problem, where the X values are continous between 0 and 1. 
        Method keyword is for future use with different relaxed solving methods. Default is Goemanns-Williamson."""

        raise ValueError('Ideal solutions for MVC are half-integral, and therefore not usable for QAOA warm_start.')
