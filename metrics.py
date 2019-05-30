# @author Piotr Nikiel <piotr.nikiel@gmail.com>

import sys
import os
import string
import pickle
sys.path.insert(0, 'FrameworkInternals')
from manage_files import get_list_classes
from transformDesign import transformDesign

def os_system_report_failure(cmd):
    """ Throws when the invocation returned non-zero """
    rv = os.system(cmd)
    if rv != 0:
        raise Exception('This command failed: {0}'.format(cmd))

def how_many_lines(path):
    f = open(path, 'r')
    lines = f.readlines()
    return len(lines)
    
def measure_file(filename):
    ''' Returns a pair of (non-empty)LoC and chars'''
    #print 'Measuring ELoC of file {0}'.format(filename)
    eloc_path = filename+'.eloc'
    os_system_report_failure('gcc -fpreprocessed -dD -E -P {0} > {1}'.format(filename, eloc_path))
    loc = how_many_lines(filename)
    eloc = how_many_lines(eloc_path)
    #print 'File {0} is: loc={1} eloc={2}'.format(filename, loc, eloc)
    return eloc


def is_string_printable(t):
    return any( c in string.ascii_letters for c in t)

def measure_file_raw(filename):
    ''' Returns a pair of (non-empty)LoC and chars'''
    f = open(filename, 'r')
    lines = filter(lambda s: is_string_printable(s), f.readlines())
    # filter lines which are whitespace only
    return len(lines)

    
def get_file_names(perspective, class_name):    
    files_per_perspective = {
        'AddressSpace':['build/AddressSpace/include/AS{0}.h', 'build/AddressSpace/src/AS{0}.cpp'],
        'Device'      :['Device/include/D{0}.h', 'Device/src/D{0}.cpp'],
        'DeviceBase'  :['build/Device/generated/Base_D{0}.h', 'build/Device/generated/Base_D{0}.cpp']
        }
    
    names = map( lambda x: x.format(class_name), files_per_perspective[perspective] )
    return names

def measure_quasar_class(class_desc):
    """ returns a dictionary of: nND (non-developer code, e.g. address-space or base of device-logic)  """
    nND = 0  # non-developer generated code
    nIC = 0  # inter-leaved code of generated and developer
    nGS = 0  # lines of only stub code
    total_lines_fully_automated = 0
    total_lines_stub = 0
    total_lines_stub_with_user_code = 0
    print '----> At class: {0}'.format(class_desc['name'])
    perspectives = ['AddressSpace']
    if class_desc['has_device_logic']:
        perspectives.append('Device')
        perspectives.append('DeviceBase')
    print '---> Class {0} has perspectives {1}'.format(class_desc['name'], perspectives)
    for perspective in perspectives:
        file_names = get_file_names(perspective, class_desc['name'])
        for file_name in file_names:
            lines = measure_file(file_name)
            print '--> File {0}: {1} ELoC'.format(file_name, lines)
            if perspective == 'AddressSpace':
                nND += lines
            elif perspective == 'Device':
                nIC += lines
            elif perspective == 'DeviceBase':
                nND += lines
    if class_desc['has_device_logic']:
        # now generate only stubs
        devicelogic_stub_h_path = 'dlstub.h'
        devicelogic_stub_cpp_path = 'dlstub.cpp'
        transformDesign(os.path.sep.join(['Device','designToDeviceHeader.xslt']), devicelogic_stub_h_path, requiresMerge=False, astyleRun=False, additionalParam="className=" + class_desc['name'])
        lines_fake = measure_file(devicelogic_stub_h_path)
        print '--> File Devicelogic h: {0} ELoc'.format(lines_fake)
        nGS += lines_fake
        transformDesign(os.path.sep.join(['Device','designToDeviceBody.xslt']), devicelogic_stub_cpp_path, requiresMerge=False, astyleRun=False, additionalParam="className=" + class_desc['name'])
        lines_fake = measure_file(devicelogic_stub_cpp_path)
        print '--> File Devicelogic cpp: {0} ELoc'.format(lines_fake)
        nGS += lines_fake
    nD = nIC - nGS # developer-written code
    if nD != 0:
        print '---> Class has {0} ELoCs of developer-written code and {1} ELoCs of generated code, so the automation factor is {2}'.format(nD, nND, float(nND+nIC)/float(nD))
    else:
        print '---> Can not print ratio because number of developer code is zero!'
    return {'nND':nND, 'nIC':nIC, 'nGS':nGS}
    

def measure_all():
    total_lines_fully_automated = 0
    total_lines_stub_with_user_code = 0
    total_lines_stub = 0
    all_classes = get_list_classes('Design/Design.xml')
    print '-----> List of classes:', map(lambda c: c['name'], all_classes)
    print '-----> Will analyze classes one by one'

    measured_all_classes = {}
    
    for class_desc in all_classes:
        measured_class = measure_quasar_class(class_desc)
        print measured_class
        for key in measured_class:
            measured_all_classes[key] = measured_all_classes.get(key, 0) + measured_class[key]


    nD = measured_all_classes['nIC'] - measured_all_classes['nGS'] # developer-written code
    nND = measured_all_classes['nND']
    ratio = float(nND+nD)/float(nD)
    print '-----> quasar-classes total: '
    print '-----> nND={0} nD={1} Automation ratio is: {2}'.format(nND, nD, ratio)
            
    nND_config_xsd = measure_file_raw('build/Configuration/Configuration.xsd')
    print '-----> Configuration: '+str(nND_config_xsd)

    nND_DeviceRoot = measure_file('build/Device/include/DRoot.h') + measure_file('build/Device/src/DRoot.cpp')
    print '-----> Device Root: {0}'.format(nND_DeviceRoot)

    nD = measured_all_classes['nIC'] - measured_all_classes['nGS'] # developer-written code
    nND = measured_all_classes['nND'] + nND_config_xsd + nND_DeviceRoot
    nIC = measured_all_classes['nIC']
    ratio = float(nND+nIC)/float(nD)
    print '-----> nD={0}'.format(nD)
    print '-----> Automation ratio is: {0}'.format(ratio)

    grand_total = measured_all_classes
    grand_total['nD'] = nD
    grand_total['nND'] = nND
    grand_total['ratio'] = ratio
    print '-----> Grand total is:'
    print grand_total
    
    f_pickle = file('QuasarMetrics.pickle', 'w')
    pickle.dump(grand_total, f_pickle)
    
if __name__ == "__main__":
    measure_all()
