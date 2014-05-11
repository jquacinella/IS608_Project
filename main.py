#!/usr/bin/python
import csv
from collections import defaultdict

# Column indicies for EIA data
UTILITY = 1
STATE = 3
COUNTY = 4

# Column indicies for EIA retail data
UTILITY_ID = 1
CONSUMPTION = 21
SHORT_CONSUMPTION = 5

# Column indicies for Census data
ID = 1
DESC = 2
POP2012 = 7

# Constants
YEAR = 2012
PATH_TO_SERVICE_DATA = "data/f8612012/service_territory_%s.csv" % YEAR  # Path to the defined utility service territories
PATH_TO_RETAIL_DATA = "data/f8612012/retail_sales_%s.csv" % YEAR  # Path to the defined utility service territories
PATH_TO_SHORTRETAIL_DATA = "data/f8612012/short_form_%s_Changed.csv" % YEAR  # Path to the defined utility service territories
PATH_TO_POPULATION_DATA = "data/PEP_2013_PEPANNRES/PEP_2013_PEPANNRES_with_ann_with_changes.csv"
STATES = { 'AK': 'Alaska','AL': 'Alabama','AR': 'Arkansas','AS': 'American Samoa','AZ': 'Arizona','CA': 'California','CO': 'Colorado','CT': 'Connecticut','DC': 'District of Columbia','DE': 'Delaware','FL': 'Florida','GA': 'Georgia','GU': 'Guam','HI': 'Hawaii','IA': 'Iowa','ID': 'Idaho','IL': 'Illinois','IN': 'Indiana','KS': 'Kansas','KY': 'Kentucky','LA': 'Louisiana','MA': 'Massachusetts','MD': 'Maryland','ME': 'Maine','MI': 'Michigan','MN': 'Minnesota','MO': 'Missouri','MP': 'Northern Mariana Islands','MS': 'Mississippi','MT': 'Montana','NA': 'National','NC': 'North Carolina','ND': 'North Dakota','NE': 'Nebraska','NH': 'New Hampshire','NJ': 'New Jersey','NM': 'New Mexico','NV': 'Nevada','NY': 'New York','OH': 'Ohio','OK': 'Oklahoma','OR': 'Oregon','PA': 'Pennsylvania','PR': 'Puerto Rico','RI': 'Rhode Island','SC': 'South Carolina','SD': 'South Dakota','TN': 'Tennessee','TX': 'Texas','UT': 'Utah','VA': 'Virginia','VI': 'Virgin Islands','VT': 'Vermont','WA': 'Washington','WI': 'Wisconsin','WV': 'West Virginia','WY': 'Wyoming'}



# Global variables
countyToUtility = {}        # Mapping from county number to a list of utilities serving it
utilityToCounty = {}        # Mapping from utility id to a list of counties it serves
countyToPopulation = {}     # Mapping from county number to a population from census data
nameToID = {}               # Mapping from county name to the county code
utilityToConsumption = dict()   # Mapping the utility id to the total consumption in mWh
utilityToPopulation = dict()    # Mapping the utility id to the total county population it serves
countyToConsumption = dict()    # Mapping the final result of county ID to consumption in mWh



def loadCensusData():
    ''' Loads the mapping from county number to population into 
    'countyToUPopulation' and a name to ID mapping from the PATH_TO_POPULATION_DATA file. '''
    f = open(PATH_TO_POPULATION_DATA)
    reader = csv.reader(f)
    reader.next()
    reader.next()
    for row in reader:
        # Grab the important parts of the data
        id = int(row[ID])
        desc = row[DESC]
        pop2012 = row[POP2012]

        # Derive the 'county key' from the description column
        (county, state) = desc.split(',')
        county = county.lower().replace("county", "").replace(".", "").replace(" ", "")
        state = state.lower().replace(' ', '')
        key = state + '_' + county

        # correction to Lousiana county names
        if state == "louisiana":
            key = key.replace("parish", "")

        # Setup the two mappings
        nameToID[key] = id
        countyToPopulation[id] = float(pop2012)


def loadCountytoUtilityData():
    ''' Loads the mapping from county number to utilities into 
    'countyToUtility' from the PATH_TO_SERVICE_DATA file. '''
    f = open(PATH_TO_SERVICE_DATA)
    reader = csv.reader(f)
    reader.next()
    for row in reader:
        state = STATES[ row[STATE].upper() ].lower().replace(' ', '')
        county = row[COUNTY].lower().replace(' ', '').replace('.', '')
        key = state + '_' + county
        utilityID = int(row[UTILITY])

        try:
            if nameToID[key] in countyToUtility:
                countyToUtility[nameToID[key]].add(utilityID)
            else:
                #if key not in nameToID:
                #    print "key %s not found" % key
                countyToUtility[nameToID[key]] = set([utilityID])

            if utilityID in utilityToCounty:
                utilityToCounty[utilityID].add(nameToID[key])
            else:
                utilityToCounty[utilityID] = set([nameToID[key]])
        except Exception as e:
            pass
            #print "Exception: %s" % key


def loadUtilityConsumptionData():
    ''' Load the retail data as  mapping from utility ID 
    to total level of consumption in mWh. '''
    # Open file as CSV and skip three header lines
    f = open(PATH_TO_RETAIL_DATA)
    reader = csv.reader(f)
    reader.next()
    reader.next()
    reader.next()

    # For each row in the reader ...
    for row in reader:
        # Read in the ID and consumption total level
        id = int(row[UTILITY_ID])
        consumption = float(row[CONSUMPTION].replace(',', ''))

        # Update global mapping
        utilityToConsumption[id] = consumption


    f = open(PATH_TO_SHORTRETAIL_DATA)
    reader = csv.reader(f)
    reader.next()

    # For each row in the reader ...
    for row in reader:
        # Read in the ID and consumption total level
        id = int(row[UTILITY_ID])
        consumption = float(row[SHORT_CONSUMPTION].replace(',', ''))

        # Update global mapping
        if id in utilityToConsumption:
            print "Whoa, we have a duplicate utility id: %d" % id

        utilityToConsumption[id] = consumption


def deriveUtilityPopulation():
    ''' Derive the total number of people in all counties served by a utility. '''

    # Loop through all utility companies and the list of counties served by them
    for utility, counties in utilityToCounty.items():
        # Calculate total population for all counties
        totPopulation = 0
        for county in counties:
            totPopulation += countyToPopulation[county]

        # Save total population in mapping
        utilityToPopulation[utility] = float(totPopulation)



def calculateCountyConsumption():
    ''' Apply our methodology and generate a mapping of county to total energy consumption in mWh. '''
    countiesWithErrors = 0
    for county, utilities in countyToUtility.items():
        # Since we are using defaultdicts, if we try to access data on a utility we do not have, 
        # it'll be counted as 0. See 'Issues' section above.
        #countyToConsumption[county] = sum([((countyToPopulation[county] / utilityToPopulation[utility]) * 
        #                                   utilityToConsumption[utility]) for utility in utilities])
        countySum = 0
        errorCount = 0

        for utility in utilities:
            try:
                countySum += ((countyToPopulation[county] / utilityToPopulation[utility]) * utilityToConsumption[utility])
            except Exception as e:
                errorCount+=1

                print "Error for county %d and utility %d" % (county, utility)

        if errorCount != 0:
            countiesWithErrors+=1
            print "Number of errors: %d / %d" % (errorCount, len(utilities))

        countyToConsumption[county] = countySum

    print "Counties with errors: %d / %d" % (countiesWithErrors, len(countyToUtility.keys()))



def main():
    # Start by loading the census data and the service territory mapping
    loadCensusData()
    loadCountytoUtilityData()
    loadUtilityConsumptionData()
    deriveUtilityPopulation()
    calculateCountyConsumption()

    #for name in nameToID:
    #    print "%s => %s" % (name, nameToID[name])

    # Count the number of counties with only one utility
    numSingle = 0
    for county in countyToUtility:
        
        #print "%s => %s" % (county, countyToUtility[county])
        
        if len(countyToUtility[county]) == 1: 
            numSingle += 1
        
        #print countyToUtility[county]

    # Print them out
    print "Number of counties: %d" % len(countyToUtility)
    print "Percentage of counties with only one utility: %f" % (numSingle / float(len(countyToUtility)))



    ###
    ### Interim D3 and Google Visualizations
    ###
    #
    # # Output CSV for Google Bar Chart
    # # NOTE: the file format is utility index and consumption total
    
    # # Sort the consumption data
    # values = utilityToConsumption.values()
    # values = sorted(values, reverse=True)
    
    # # Open a CSV writer to the CSV file
    # writer = csv.writer(open("barchart.csv", "w"))

    # # Write header
    # writer.writerow(['index','consumption'])

    # # Loop over data and write out idx, consumption pair to CSV
    # idx = 0
    # for consumption in values:
    #     if consumption != 0:
    #         writer.writerow([idx, consumption])
    #         idx+=1

    # # Output CSV for D3 diagram. 
    # # NOTE: This is a CSV file of links in a mathematical graph where the source is the county, 
    # # the target is the utility and the link has a weight of 1
    
    # # Open a CSV writer to the CSV file
    # writer = csv.writer(open("network.csv", "w"))

    # # Write header
    # writer.writerow(['source','target','value'])

    # # For each county to utility pair ...
    # count = 0
    # for (county, utilities) in countyToUtility.items():

    #     # ... Output links to CSV file 
    #     for utility in utilities:
    #         writer.writerow([county, utility, 10.0])
    #         count+=1
        
    #     # But only do up to MAX_GRAPH since it'll get too large too quickly
    #     if count >1000:
    #         break;


    # Output CSV for choropleth maps
    f = open("map.csv", "w")
    f.write("id,consumption\n")
    for county, consumption in countyToConsumption.items():
        f.write("%s,%s\n" % (county, consumption))
    f.close()

    # Max consumption (so we can set the scale in html)
    print("Max: %f" % max(countyToConsumption.values()))

if __name__ == "__main__":
    main()