"""
SiEPIC Photonics Package

Author:     Mustafa Hammood
            Mustafa@siepic.com
            
            https://github.com/SiEPIC-Kits/SiEPIC_Photonics_Package

Module:     Core functionalities of SiEPIC PP

functions:

calibrate( input_response, reference_response): response correction function to calibrate an input response with respect to a reference response
calibrate_envelope( input_response, reference_response): response correction function to calibrate an input response with respect to the envelope of a reference response
baseline_correction( input_response ): baseline correction function to flatten a response with respect to it self
cutback( input_data_response, input_data_count, wavelength): extract insertion losses of a structure using cutback method
to_s_params( input_data ):
download_response (url, port): downloads input .mat response from a url and parses data into array
"""

from SiEPIC_Photonics_Package.setup import *

#%% calibration function

def calibrate( input_response, reference_response):
    # calibrate( input_response, reference_response): response correction function to calibrate an input response with respect to a reference response
    # input list format: [input_response[wavelength (nm), power (dBm)], reference_response[wavelength (nm), power (dBm)]]
    # output list format: [input power (dBm) with calibration correction, polynomial fit of reference power (dBm)]
    
    # fit the calibration response to a polynomial
    fitOrder = 8
    wavelength = reference_response[0]
    power = reference_response[1]
    
    pfit = numpy.polyfit(wavelength-numpy.mean(wavelength), power, fitOrder)
    power_calib_fit = numpy.polyval(pfit, wavelength-numpy.mean(wavelength))
    
    power_corrected = input_response[1] - power_calib_fit
    
    return [power_corrected, power_calib_fit]

#%% baseline_correction function (useful to normalize and calibrate periodic responses)
def baseline_correction( input_response ):
    #baseline_correction( input_response ): baseline correction function to flatten a response with respect to it self
    # input list format: input_response[wavelength (nm), power (dBm)]
    # output list format: [input power (dBm) with baseline correction, baseline correction fit]
        
    fitOrder = 4
    wavelength = input_response[0]
    power = input_response[1]
    
    pfit = numpy.polyfit(wavelength-numpy.mean(wavelength), power, fitOrder)
    power_baseline = numpy.polyval(pfit, wavelength-numpy.mean(wavelength))
    
    power_corrected = power - power_baseline
    power_corrected = power_corrected + max(power_baseline) -max(power)
    
    return [power_corrected, power_baseline]

#%% calibrate a response based on an envelope response (useful for non-periodic responses, i.e. Bragg)
def calibrate_envelope( input_response, reference_response, seg = 55, difference_tol = 8, fitOrder = 4):
    # step 1-pick points on the reference response that create an envelope fit
    # split the response into SEG segments, if two segments are seperated by more than TOL, discard second point and go to next point
    wavelength = reference_response[0]
    power = reference_response[1]

    wavelength_input = input_response[0]
    power_input = input_response[1]

    step = int(numpy.size(power)/seg)

    power_ref = []
    wavelength_ref = []
    cursor_initial = 0
    cursor_next = 1
    for i in range(seg):

        point_initial = power[cursor_initial*step]
        point_next = power[step*(cursor_next)]
        
        if abs(point_initial - point_next) < difference_tol:              
            power_ref.append(power[cursor_initial*step])
            wavelength_ref.append(wavelength[cursor_initial*step])
            cursor_initial = cursor_initial+1
            cursor_next = cursor_next+1
        else:
            while abs(point_initial - point_next) > difference_tol and (cursor_next+2)*step < numpy.size(power):
                cursor_next = cursor_next+1
                point_next = power[step*(cursor_next)]
                
            cursor_initial = cursor_next
            cursor_next = cursor_next+1


        if cursor_next*step >= numpy.size(power):
            break
    
    pfit_ref = numpy.polyfit(wavelength_ref-numpy.mean(wavelength_ref), power_ref, fitOrder)
    powerfit_ref = numpy.polyval(pfit_ref, wavelength-numpy.mean(wavelength))
    
    pfit_input = numpy.polyfit(wavelength_input-numpy.mean(wavelength_input), power_input, fitOrder)
    powerfit_input = numpy.polyval(pfit_input, wavelength_input-numpy.mean(wavelength_input))
    
    # step 2-call calibrate input with envelope fit as a reference response
    power_input_calibrated = power_input - powerfit_ref
    
    return [power_input_calibrated, powerfit_ref]

#%% cutback function
def cutback( input_data_response, input_data_count, wavelength):
    #cutback( input_data_response, input_data_count, wavelength): extract insertion losses of a structure using cutback method
    # input list format: input_data_response (list) [wavelength (nm), power (dBm)]
    #                   input_data_count (array) [array of unit count]
    #                   wavelength of insertion loss measurement
    # output list format: [insertion loss (fit) at wavelength (dB/unit), insertion loss (dB) vs wavelength (nm)]
    # fit the responses to a polynomial
    fitOrder = 8
    wavelength_data = input_data_response[0][0]
    
    power = []
    pfit = []
    power_fit = []
    for i in range(len(input_data_count)):
        power.append( input_data_response[i][1] )
        pfit.append( numpy.polyfit(wavelength_data-numpy.mean(wavelength_data), power[i], fitOrder) )
        power_fit.append( numpy.polyval(pfit[i], wavelength_data-numpy.mean(wavelength_data)) )
    
    power_fit_transpose = numpy.transpose(power_fit)
    power_transpose = numpy.transpose(power)
    
    # find index of wavelength of interest
    index = numpy.where( wavelength_data==wavelength )[0][0]
    
    # find insertion loss vs wavelength
    insertion_loss = []
    insertion_loss_raw = []
    for i in range(len(wavelength_data)):
        insertion_loss.append( numpy.polyfit(input_data_count, power_fit_transpose[i], 1))
        insertion_loss_raw.append( numpy.polyfit(input_data_count, power_transpose[i], 1))
    
    
    return [ insertion_loss[index][0], numpy.transpose(insertion_loss)[0], numpy.transpose(insertion_loss_raw)[0] ]

#%% to_s_params function
def to_s_params( input_data ):
    return

#%% download_response function
def download_response ( url, port):
    # download_response (url, port): downloads input .mat response from a url and parses data into array
    # input: (.mat data download url, port response) 
    # outputs parsed data array [wavelength (m), power (dBm)]
    # data is assumed to be from automated measurement scanResults or scandata format
    r = requests.get(url,allow_redirects=True)
    file_name = 'downloaded_data'+str(port)
    with open(file_name, 'wb') as f:
        f.write(r.content)
        
    data = scipy.io.loadmat(file_name)
    
    if( 'scanResults' in data ):
        wavelength = data['scanResults'][0][port][0][:,0]
        power = data['scanResults'][0][port][0][:,1]
    elif( 'scandata' in data ):
        wavelength = data['scandata'][0][0][0][:][0]
        power = data['scandata'][0][0][1][:,port]
    elif( 'wavelength' in data ):
        wavelength = data['wavelength'][0][:]
        power = data['power'][:,port][:]
    
    data = [wavelength,power]
    return data

#%% parse_response function (local files version)
def parse_response ( filename, port):
    # parse_response (filename, port): parses an input .mat response from a local file and parses data into array
    # input: (.mat data download filename, port response) 
    # outputs parsed data array [wavelength (m), power (dBm)]
    # data is assumed to be from automated measurement scanResults or scandata format
    data = scipy.io.loadmat(filename)
    
    if( 'scanResults' in data ):
        wavelength = data['scanResults'][0][port][0][:,0]
        power = data['scanResults'][0][port][0][:,1]
    elif( 'scandata' in data ):
        wavelength = data['scandata'][0][0][0][:][0]
        power = data['scandata'][0][0][1][:,port]
    elif( 'wavelength' in data ):
        wavelength = data['wavelength'][0][:]
        power = data['power'][:,port][:]
    
    data = [wavelength,power]
    return data

#%% bandwidth function
# find nearest index to value in a numpy array
def find_nearest(array, value):
    array = numpy.asarray(array)
    idx = (numpy.abs(array - value)).argmin()
    return idx

def bandwidth ( input_data_response, threshold = 3):
    # bandwidth (filename, port): parses an input .mat response from a local file and parses data into array
    # input list format: input_data_response (list) [wavelength (nm), power (dBm)]
    #                    bandwidth threshold, default 3 dB
    # output list format: [bandwidth of threshold, central wavelength]

    wavelength = input_data_response[0]
    response = input_data_response[1]
    
    center_index = find_nearest( response, max(response))
    isInBand = response>max(response) - threshold

    leftBound = center_index

    while isInBand[leftBound] == 1:
        leftBound = leftBound-1

    rightBound=center_index

    while isInBand[rightBound] == 1:
        rightBound = rightBound+1

    bandwidth = wavelength[rightBound] - wavelength[leftBound]
    
    central_wavelength = (wavelength[rightBound] + wavelength[leftBound])/2
    
    return [bandwidth, central_wavelength]
    
    