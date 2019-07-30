"""
Created on Tue Jul 30 11:45:00 2019

@author: Stuart J. Robbins

This code takes in a crater rim trace, in decimal degrees, and determines if any
component of the trace meets set criteria for being considered an approximately
straight edge, and if any component between two edges meets criteria to be
considered a hinge.  It creates a graph showing the results and outputs the data
to the command line.

"""


##TO DO:  SEE "TO DO" ITEMS THROUGHOUT THIS FILE.



#Import the libraries needed for this program.
import argparse                     #allows parsing of input options
import numpy as np                  #lots of maths
import scipy as sp                  #lots of special maths
import math                         #other lots of maths
import time                         #timing for debugging
import sys                          #for setting NumPY output for debugging
import matplotlib.pyplot as mpl     #for display purposes

#Set any code-wide parameters.
np.set_printoptions(threshold=sys.maxsize) #for debugging purposes


#General help information.
parser = argparse.ArgumentParser(description='Identify polygonal crater rims.')

#Various runtime options.
parser.add_argument('--input',          dest='inputFile',       action='store', default='', help='Name of the CSV file with a single crater rim trace with latitude,longitude in decimal degrees, one per line.')
parser.add_argument('--body_radius',    dest='d_planet_radius', action='store', default='1',help='Radius of the planetary body on which the crater is placed, in kilometers.')
parser.add_argument('--tolerance_distance_min_forside',     dest='tolerance_distance_min_forside',  action='store', default='5',    help='The minimum length of a rim segment to be approximately straight to be considered an edge (in km).')
parser.add_argument('--tolerance_distance_max_forhinge',    dest='tolerance_distance_max_forhinge', action='store', default='5',    help='The maximum length of a rim segment to be curved enough to be considered a hinge/joint between edges (in km).')
parser.add_argument('--tolerance_angle_max_forside',        dest='tolerance_angle_max_forside',     action='store', default='10',   help='The maximum angle that a rim segment can vary for it to be considered a straight side (in degrees).')
parser.add_argument('--tolerance_angle_min_forhinge',       dest='tolerance_angle_min_forhinge',    action='store', default='20',   help='The minimum standard deviation of the bearing angle a rim segment must vary within the given length for it to be considered a hinge/joint between edges (in degrees).')

#Parse all the arguments so they can be stored
args=parser.parse_args()




##----------------------------------------------------------------------------##

#Store the time to output it at the end.
timer_start = time.time()
tt = time.time()



##-------------- SET UP THE DATA INTO A LOCAL COORDINATE SYSTEM --------------##


#Read the crater rim data.
rim_data = np.genfromtxt(args.inputFile,delimiter=',')

#Create some variables and vectors for use in transforms.  The center-of-mass
# variables are not standard because sometimes we do not have complete rims, and
# this helps get closer to the real center.
x_center_mass_degrees = (np.mean(rim_data[:,0])+(np.min(rim_data[:,0])+np.max(rim_data[:,0]))/2.)/2.
y_center_mass_degrees = (np.mean(rim_data[:,1])+(np.min(rim_data[:,1])+np.max(rim_data[:,1]))/2.)/2.
rim_lon_temp = np.copy(rim_data[:,0])
rim_lat_temp = np.copy(rim_data[:,1])
dist        = [0]*(len(rim_data))
bearing     = [0]*(len(rim_data))
atan2_part1 = [0]*(len(rim_data))
atan2_part2 = [0]*(len(rim_data))

#Determine the distance to each rim point from the {x,y} center of mass using
# Great Circles (Vincenty, 1975).
dist[:] = np.power(np.sin((rim_data[:,1]-y_center_mass_degrees)*math.pi/180/2),2) + np.cos(rim_data[:,1]*math.pi/180)*np.cos(y_center_mass_degrees*math.pi/180)*np.power((np.sin((rim_data[:,0]-x_center_mass_degrees)*math.pi/180/2)),2)
dist[:] = 2*np.arctan2(np.sqrt(dist[:]),np.sqrt(1.0 + np.negative(dist[:]))) * float(args.d_planet_radius)

#Calculate the positions of each rim point in {x,y} via calculating the angles
# between the original points and the center of mass, using bearings (Vincenty,
# 1975).  This is unfortunately a long set of equations so I have put it off
# into a separate function that returns the initial azimuth (i.e., the initial
# bearing between the center of mass and the end lat/lon; technically, bearing
# changes as you move along the Great Circle arc).
atan2_part1[:]  = np.sin((rim_lon_temp[:]-x_center_mass_degrees)*math.pi/180)*np.cos(rim_lat_temp*math.pi/180)
atan2_part2[:]  = np.cos(y_center_mass_degrees*math.pi/180)*np.sin(rim_lat_temp[:]*math.pi/180) - np.sin(y_center_mass_degrees*math.pi/180)*np.cos(rim_lat_temp[:]*math.pi/180)*np.cos((rim_lon_temp[:]-x_center_mass_degrees)*math.pi/180)
bearing[:]      = np.arctan2(atan2_part1[:], atan2_part2[:])*180./math.pi  #where this is -180° to +180°, clockwise, and due North is 0°

#THIS IS AN APPROXIMATION and ideally should actually trace Great Circles from
# the center of mass to the original rim points.  Instead, this just uses the
# sine and cosine components of the bearing from the center of mass to re
# -project the rim points.
rim_lon_temp[:] = dist[:] * np.sin(np.multiply(bearing[:],math.pi/180.))
rim_lat_temp[:] = dist[:] * np.cos(np.multiply(bearing[:],math.pi/180.))



##--------- CALCULATE DISTANCE AND BEARING VECTORS OF THE RIM TRACE ----------##

#Re-purpose the "dist" vector to make it equal to the distance between each
# point as you walk around the polygon.
dist[0:-1]  = np.power((np.sin((rim_data[1:,1]-rim_data[0:-1,1])*math.pi/180/2)),2) + np.cos(rim_data[1:,1]*math.pi/180)*np.cos(rim_data[0:-1,1]*math.pi/180)*np.power(np.sin((rim_data[1:,0]-rim_data[0:-1,0])*math.pi/180/2),2)
dist[-1]    = np.power((np.sin((rim_data[0 ,1]-rim_data[-1  ,1])*math.pi/180/2)),2) + np.cos(rim_data[0 ,1]*math.pi/180)*np.cos(rim_data[-1  ,1]*math.pi/180)*np.power(np.sin((rim_data[0  ,0]-rim_data[-1 ,0])*math.pi/180/2),2)
dist[:]     = 2*np.arctan2(np.sqrt(dist[:]),np.sqrt(1.0 + np.negative(dist[:]))) * float(args.d_planet_radius)

#Integrate the distances to put the sum at the NEXT point, so point index 1 has
# the distance between point index 0 and 1.
#TO DO: Python-ize.
dist_INT = [0]*(len(rim_data)+1)
for iCounter in range(1,len(dist_INT)):
    dist_INT[iCounter] = dist_INT[iCounter-1] + dist[iCounter-1]

#Re-purpose the "bearing" vector to make it equal to the bearing between each
# point as you walk around the polygon.
atan2_part1[0:-1] = np.sin((rim_data[1:,0]-rim_data[0:-1,0])*math.pi/180)*np.cos(rim_data[1:,1]*math.pi/180)
atan2_part1[  -1] = np.sin((rim_data[0 ,0]-rim_data[  -1,0])*math.pi/180)*np.cos(rim_data[0 ,1]*math.pi/180)
atan2_part2[0:-1] = np.cos(rim_data[0:-1,1]*math.pi/180)*np.sin(rim_data[1:,1]*math.pi/180) - np.sin(rim_data[0:-1,1]*math.pi/180)*np.cos(rim_data[1:,1]*math.pi/180)*np.cos((rim_data[1:,0]-rim_data[0:-1,0])*math.pi/180)
atan2_part2[  -1] = np.cos(rim_data[  -1,1]*math.pi/180)*np.sin(rim_data[0 ,1]*math.pi/180) - np.sin(rim_data[  -1,1]*math.pi/180)*np.cos(rim_data[0 ,1]*math.pi/180)*np.cos((rim_data[0 ,0]-rim_data[  -1,0])*math.pi/180)
bearing           = np.arctan2(atan2_part1, atan2_part2)*180./math.pi   #where this is -180° to +180°, clockwise, and due North is 0°

#Make the bearing continuous when we go over +180°.
#TO DO: Python-ize.
for iCounter in range(1,len(bearing)):
    bearing[iCounter] = bearing[iCounter]+360. if np.abs(bearing[iCounter]-bearing[iCounter-1])>180. else bearing[iCounter]

#But, what we actually want is the DIFFERENCE in bearing from one point to the
# next, but not quite, we want this point relative to surrounding ones, so we
# will differentiate using the central difference method.
#TO DO: Python-ize.
bearing_DIF = [0]*(len(rim_data))
bearing_DIF[0] = bearing[1]-bearing[0]
bearing_DIF[len(bearing_DIF)-1] = bearing[len(bearing_DIF)-1]-bearing[len(bearing_DIF)-2]
for iCounter in range(1,len(bearing_DIF)-2):
    bearing_DIF[iCounter] = ( (bearing[iCounter+1]-bearing[iCounter]) + (bearing[iCounter]-bearing[iCounter-1]) ) / 2.



##----------------------- PERFORM THE POLYGON ANALYSIS -----------------------##

#Vectors and Variables.
array_sides  = []       #stores as a tuple the indices of the start and end of any edge
array_angles = []       #stores the average bearing of any found edge
array_length = []       #stores the length along the rim for any found edge
counter_point_start = 0

#Large loop to do the math.  This loop will walk around the crater rim and,
# based on the four command-line argument tolerances, will determine if and
# where there are any polygonal edges and/or hinges.  Rather than explain how it
# works up here, I will walk you through it as we go.  To start off with, we are
# going to loop through each point along the rim and determine if there are any
# edges or hinges from each point.  But, if we find one, we skip to the end of
# it to determine any remaining, such that this is set up as a while-True loop
# instead of for() loop because Python does not allow you to dynamically alter
# the iterating variable within the loop itself.
while True:
    
    #For the initial search from this starting point, we need the index of the
    # first possible end point for this edge, which is based on distance.
    counter_point_end = round(np.searchsorted(dist_INT, dist_INT[counter_point_start]+float(args.tolerance_distance_min_forside)))
    
    #NumPY will NOT return an error if the search is before or after the list,
    # so we need to check for that.
    if (counter_point_end > 0) and (counter_point_end < len(dist_INT)):
        
        #We have a set of points that could be an edge because it's long enough.
        # The first step in testing it is to calculate the standard deviation.
        # In this calculation, we want the end points to be inclusive, so we
        # need to slice up to +1.  We also want the sample standard deviation,
        # not the population standard deviation, so need to use ddof=1.
        standardDeviation = np.std(bearing[counter_point_start:counter_point_end+1], ddof=1)
        
        #Now, test that standard deviation.
        if(standardDeviation <= float(args.tolerance_angle_max_forside)):
            
            #We successfully found points that can be considered a side, so now
            # want to look further along the rim to determine if any more
            # contiguous points could be considered part of this side, too.
            while True:
                counter_point_end += 1
                standardDeviation = np.std(bearing[counter_point_start:counter_point_end+1], ddof=1)
                if standardDeviation > float(args.tolerance_angle_max_forside):
                    counter_point_end -= 1  #subtract 1 because we went over
                    break
            
            #We have our maximum-length rim section that qualifies as an edge,
            # so now re-calculate the standard deviation of the bearing of the
            # points within it.
            reference_standardDeviation = standardDeviation = np.std(bearing[counter_point_start:counter_point_end+1], ddof=1)
            
#            #Determine if we want to contract the edge at all.  This is only
#            # potentially -1 rim point on either end and is going to be done if
#            # removing the point significantly shrinks the standard deviation of
#            # the bearing of the full edge identified above.
#            flag_start_increase = 0
#            flag_stop_decrease  = 0
#            standardDeviation = np.std(bearing[counter_point_start+1:counter_point_end+1], ddof=1)
#            if reference_standardDeviation > 1.25*standardDeviation:
#                flag_start_increase += 1
#            standardDeviation = np.std(bearing[counter_point_start:counter_point_end], ddof=1)
#            if reference_standardDeviation > 1.25*standardDeviation:
#                flag_stop_decrease   += 1
#            counter_point_start += flag_start_increase
#            counter_point_end   += flag_stop_decrease

            #TO DO:  See if shifting the edge back-and-forth at all allows it to
            # be extended, such as by lower standard deviation.

            #Now that we have the for-realz edge start/end indices, store them.
            array_sides.append([counter_point_start,counter_point_end+1])
#            print("side",array_sides[len(array_sides)-1])

            #Since we have a real edge, store the average bearing of this side.
            array_angles.append(np.mean(bearing[counter_point_start:counter_point_end+1]))

            #Since we have a real edge, store the length along the rim for it.
            array_length.append(dist_INT[counter_point_end+1]-dist_INT[counter_point_start])
            
            #Set up to testfor another edge at the end of this one.
            counter_point_start = counter_point_end+1
        
        #The standard deviation of the minimum-length side was too large, so it
        # does not count as an edge and we have to move on, starting with the
        # next point as the possible start location.
        else:
            counter_point_start += 1
    
    #The distance measure for an edge failed to find something within the list,
    # so we should move on.
    #TO DO: This is where wrap-around code needs to be developed.
    else:
        counter_point_start += 1

    #Our only, singular quit criterion.
    if counter_point_start > len(dist)-1:
        break


#Now determine if the possible hinges meet the criteria set by the command-line
# arguments for maximum distance and minimum angle.  Special case for the last
# candidate hinge to support wrap-around.
array_hinge_valid = [0]*(len(array_angles)) #holds a boolean array
for counter_hinge in range(0,len(array_angles)-1):
    if(dist_INT[array_sides[counter_hinge+1][0]]-dist_INT[array_sides[counter_hinge][1]] < float(args.tolerance_distance_max_forhinge)):
        if(array_angles[counter_hinge+1]-array_angles[counter_hinge] > float(args.tolerance_angle_min_forhinge)):
            array_hinge_valid[counter_hinge] = 1
if(dist_INT[array_sides[0][0]]+(dist_INT[len(dist_INT)-1]-dist_INT[array_sides[len(array_angles)-1][1]]) < float(args.tolerance_distance_max_forhinge)):
    if((array_angles[0]+360)-array_angles[len(array_angles)-1] > float(args.tolerance_angle_min_forhinge)):
        array_hinge_valid[counter_hinge] = 1


##Debug purposes.
#print(array_sides)
#print(array_angles)
#print(array_length)
#print(array_hinge_valid)



##------------------------ OUTPUT RESULTS TO THE USER ------------------------##

print("\nThere were %g edges and %g hinges found.  Data follows for each.\n" % (len(array_sides), np.sum(array_hinge_valid)))
for iCounter, edge in enumerate(array_sides):
    print(" Edge #%g" % int(iCounter+1))
    print("   Start (Latitude, Longitude):", rim_data[edge[0],0], rim_data[edge[0],1])
    print("   End   (Latitude, Longitude):", rim_data[edge[1],0], rim_data[edge[1],1])
    print("   Length (km)                :", array_length[iCounter])
    print("   Bearing (degrees, N=0°, CW):", array_angles[iCounter])
for iCounter, hinge in enumerate(array_hinge_valid):
    if hinge == 1:
        print(" Candidate Hinge #%g" % int(iCounter+1))
        print("   Length (km)               :", dist_INT[array_sides[iCounter+1][0]]-dist_INT[array_sides[iCounter][1]])
        print("   Angle  (degrees, N=0°, CW):", array_angles[iCounter+1]-array_angles[iCounter])
    else:
        print(" Candidate Hinge #%g failed to meet tolerances." % int(iCounter+1))



##--------------------------------- DISPLAY ----------------------------------##

#I'm going to comment this as though you do not know anything about Python's
# graphing capabilities with MatPlotLib.  Because I don't know anything about it

#Create the plot reference.
PolygonalCraterWindow = mpl.figure(1, figsize=(10,10))


#Plot the crater rim.
mpl.plot(rim_data[:,0], rim_data[:,1], color='#666666', linewidth=3, label='Rim Trace')


#Append a line for every valid edge.
for iCounter in range(len(array_sides)):

    #For the idealized edges, we can't simply take the start point and graph to
    # the end point.  Instead, we take the center lat/lon of each edge and
    # extend it outwards to the edge end, assuming simple linear projection.
    #*****WARNING*****: This will not be accurate on small bodies!!
    #TO DO: Take the average center and trace out Great Circles for the edges
    # instead of just drawing a straight line.
    center_x = np.mean(rim_data[array_sides[iCounter][0]:array_sides[iCounter][1],0])
    center_y = np.mean(rim_data[array_sides[iCounter][0]:array_sides[iCounter][1],1])
    length_x = abs(dist_INT[array_sides[iCounter][0]] - dist_INT[array_sides[iCounter][1]]) * np.sin(array_angles[iCounter]*math.pi/180.)
    length_y = abs(dist_INT[array_sides[iCounter][0]] - dist_INT[array_sides[iCounter][1]]) * np.cos(array_angles[iCounter]*math.pi/180.)
    length_x *= 360./(2.*float(args.d_planet_radius)*math.pi)
    length_y *= 360./(2.*float(args.d_planet_radius)*math.pi)

    linesegment_x = [center_x-length_x/2., center_x+length_x/2.]
    linesegment_y = [center_y-length_y/2., center_y+length_y/2.]
    linesegment_x_extended = [center_x-length_x/2.*2.0, center_x+length_x/2.*2.0]
    linesegment_y_extended = [center_y-length_y/2.*2.0, center_y+length_y/2.*2.0]

    #Append the lines for this edge.
    if iCounter == 0:
        mpl.plot(linesegment_x_extended, linesegment_y_extended, color='#FFAAAA', linewidth=1, dashes=[5,5], label='Edges Extended')
        mpl.plot(linesegment_x, linesegment_y, color='#FF0000', linewidth=2, label='Edges')
    else:
        mpl.plot(linesegment_x_extended, linesegment_y_extended, color='#FFAAAA', linewidth=1, dashes=[5,5])
        mpl.plot(linesegment_x, linesegment_y, color='#FF0000', linewidth=2)

#Append a symbol for every valid hinge.
array_hinges_x_position = []
array_hinges_y_position = []
for iCounter, validHinge in enumerate(array_hinge_valid):
    if validHinge == 1:
        array_hinges_x_position.append([(rim_data[int(round((array_sides[iCounter+1][0] + array_sides[iCounter][1]) / 2.))][0])])
        array_hinges_y_position.append([(rim_data[int(round((array_sides[iCounter+1][0] + array_sides[iCounter][1]) / 2.))][1])])
mpl.scatter(array_hinges_x_position, array_hinges_y_position, s=250, facecolors='none', edgecolors='#0000FF', label='Hinges')


##General graph appendages.

#Append the legend to the plot.
mpl.legend(loc='upper right')

#Append axes labels.
mpl.xlabel('Longitude (degrees)')
mpl.ylabel('Latitude (degrees)')

#Append graph title.
mpl.title('Crater Rim with Any Polygonal Edges and Angles')


##Finally, make the plot visible.
mpl.show()