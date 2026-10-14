
## /!\ On pourrait implémenter chaque objet sous forme d'une classe avion 

#######################################################################
################# Parameters (Boeing 737-800) (5.5.1) #################
#######################################################################

"""Geometry and Aerodynamic (Boeing 737-800)"""

S = 124.6 # reference surface - m^2
C_L_MAX = 2.1 # Max lift - 
C_D_0 = 0.0780 # Drag at lift 0 - 
K = 0.0366 # Induced drag factor - 
K_VS1G_MIN = 1.13 # Minimum speed margin factor - 


"""Propulsion System (CFM56-7B24 engines) """

N_ENGINES = 2 # Number of engines
F_TO_BASE: 117.000 # Take-off thrust per engine - N
F_CLIMB_BASE: 117.000 # Climb thrust per engine - N

# To complete

""" Operational Parameters"""

#### To complete

""" Atmosphere Constants """

T0 = 15 # sea-level standard temperature - celsius
L = 0.0065 # temperature lapse rate - K/m
P0 = 101,325 # sea-level standard temperature - Pa
G0 = 9.80665 # standard gravitational acceleration - m/s^2
R = 287.05 # specific gas constant for air - J/(kg·K)
RHO_0 = 1.225 # sea-level standard density - kg/m^3
CP = 0.985 # empirical correction factor accounting for typical atmospheric humidity effects - 



"""
/!\ 
Note: While the methodology is adaptable to other commercial aircraft types spanning re-
gional jets through wide-body configurations (Section 1.4.2), the climate impact analysis
presented in subsequent chapters focuses exclusively on the Boeing 737-800 as a represen-
tative narrow-body aircraft. Extension to additional aircraft types, including the Airbus
A320 family, forms a natural direction for future research.
/!\
Does it mean adapting is not as easy as parametrization ?
"""


#######################################################################
############## Atmospheric Property Calculations (5.5.2) ##############
#######################################################################

## /!\ Valid under 11000 meters (ok for commercial aircraft), add range checking ?

def Temperature_ISA(h:float):
    """Temperature variation with altitude following the tropospheric lapse rate

    Args:
        h (float): geometric altitude in meters

    Returns:
        float: Temperature ISA at h
    """    
    return T0 - L*h

def Temperature_actual(h:float):
    """Actual temperature at a given altitude is specified as deviation from ISA: T = T_ISA + deltaT_ISA. To implement

    Args:
        h (float): geometric altitude in meters
    """    
    return 


def Pressure_actual(h:float):
    """Pressure variation with altitude follows from hydrostatic equilibrium under constant lapse rate

    Args:
        h (float): geometric altitude in meters

    Returns:
        float: Pressure at h
    """    
    return P0 * (1 - L*h/T0)^(G0/(R*L))

def Rho(h:float):
    return RHO_0 * (Pressure_actual(h)/P0) * (Temperature_ISA(0)/Temperature_actual(h)) * CP


#######################################################################
##################### Thrust calculation (5.5.3) ######################
#######################################################################


