
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
K_DER_TO = 900 # Take-off thrust derate rate - N/°C
K_DER_CLIMB = 850 # Climb thrust derate rate - N/°C

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

def Temperature_flat(h:float):
    if h>0:
        return Temperature_ISA(h)+15
    elif h==0:
        return 30

def delta_T_isa(h,Temp):
    return Temp - Temperature_ISA(h)


####################################################################################################################
################# Thrust Calculation with Temperature Derate and Altitude Corrections (5.5.3) ######################
####################################################################################################################

def Fto(h:float,Temp:float):
    """Determine temperature regime and compute base thrust

    Args:
        h (float): geometric altitude in meters
        Temp (float): Actual temperature

    Returns:
        float: base thrust
    """    
    if delta_T_isa(h,Temp)<Temperature_flat(h):
        Fto=F_TO_BASE
    else:
        Fto=F_TO_BASE-K_DER_TO*(delta_T_isa(h,Temp)-Temperature_flat(h))
    Fto_corrected=correct_thrust(Fthrust=Fto,h=h)
    return max(Fto_corrected,0.35*F_TO_BASE)

def F_climb(h:float,Temp):
    """Determine temperature regime and compute base thrust

    Args:
        h (float): geometric altitude in meters
        Temp (float): Actual temperature in °C

    Returns:
        float: base climb thrust
    """    
    if delta_T_isa(h,Temp)<Temperature_flat(h):
        Fclimb=F_CLIMB_BASE
    else:
        Fclimb=F_CLIMB_BASE*(delta_T_isa(h,Temp)-Temperature_flat(h))
    Fclimb_corrected=correction_factor(Fclimb,h)
    return max(Fclimb_corrected,0.35*F_CLIMB_BASE)
    
def correction_factor(h:float):
    """ From the paper: 
      /Validation studies revealed systematic altitude-dependent bias requiring empirical correction.
      The implementation provides multiple altitude correction options enabling 
      investigation of different scaling methodologies/
      Determine a scale factor

    Args:
        h (float): geometric altitude in meters

    Returns:
        float: scale factor
    """    
    
    if True:
        return 1.0
    elif False:
        return Rho(h)/RHO_0 # Density correction scales thrust proportionally to density ratio.
    elif False:
        return 1-0.025*(h/1000) # Reduced linear penalty applies 2.5% reduction per 1000 meters altitude.
    elif False:
        return 1-0.06*(h/1000) # Traditional linear penalty applies 6% reduction per 1000 meters altitude, representing conservative operational rule-of-thumb

def correct_thrust(Fthrust:float,h:float):
    """correct the climb and TO thrust following the chosen correction factor

    Args:
        Fthrust (float): Thrust to correct in N
        h (float): geometric altitude in meters

    Returns:
        float: corrected thrust
    """    
    return Fthrust*correction_factor(h)






