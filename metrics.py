# @author Piotr Nikiel <piotr.nikiel@gmail.com>

import sys
import os
import string
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
    
def get_file_names(perspective, class_name):    
    files_per_perspective = {
        'AddressSpace':['build/AddressSpace/include/AS{0}.h', 'build/AddressSpace/src/AS{0}.cpp'],
        'Device'      :['Device/include/D{0}.h', 'Device/src/D{0}.cpp'],
        'DeviceBase'  :['build/Device/generated/Base_D{0}.h', 'build/Device/generated/Base_D{0}.cpp']
        }
    
    names = map( lambda x: x.format(class_name), files_per_perspective[perspective] )
    return names
    
def measure_all():
    total_lines_fully_automated = 0
    total_lines_stub_with_user_code = 0
    total_lines_stub = 0
    all_classes = get_list_classes('Design/Design.xml')
    print '-----> List of classes:', map(lambda c: c['name'], all_classes)
    print '-----> Will analyze classes one by one'
    for class_desc in all_classes:
        print '----> At class: {0}'.format(class_desc['name'])
        perspectives = ['AddressSpace']
        if class_desc['has_device_logic']:
            perspectives.append('Device')
            perspectives.append('DeviceBase')
        print '---> Class {0} has perspectives {1}'.format(class_desc['name'], perspectives)
        for perspective in perspectives:
            names = get_file_names(perspective, class_desc['name'])
            
            #print 'processing class='+class_desc['name']+ ': '+str(names)
            for name in names:
                lines = measure_file(name)
                print '--> File {0}: {1} ELoC'.format(name, lines)
                if perspective == 'AddressSpace':
                    total_lines_fully_automated += lines
                elif perspective == 'Device':
                    total_lines_stub_with_user_code += lines
                elif perspective == 'DeviceBase':
                    total_lines_fully_automated += lines
        if class_desc['has_device_logic']:
            # now generate only stubs
            transformDesign(os.path.sep.join(['Device','designToDeviceHeader.xslt']), 'fakeout.txt', 0, 0, "className=" + class_desc['name'])
            lines_fake = measure_file('fakeout.txt')
            print 'fake lines:'+str(lines_fake)
            total_lines_stub += lines_fake
            transformDesign(os.path.sep.join(['Device','designToDeviceBody.xslt']), 'fakeout.txt', 0, 0, "className=" + class_desc['name'])
            lines_fake = measure_file('fakeout.txt')
            total_lines_stub += lines_fake

    config_xsd = measure_file('build/Configuration/Configuration.xsd')
    print 'Configuration: '+str(config_xsd)
                    
    total_lines_fully_automated += config_xsd
    total_lines_fully_automated += total_lines_stub
    print 'Fully automated lines: '+str(total_lines_fully_automated)
    print 'Stub with user code: '+str(total_lines_stub_with_user_code)
    print 'Raw stub: '+str(total_lines_stub)
    user_code_lines = total_lines_stub_with_user_code - total_lines_stub
    print 'User code lines: '+str(user_code_lines)+'   reduction='+str((total_lines_stub_with_user_code+total_lines_fully_automated)/float(user_code_lines))
    

if __name__ == "__main__":
    measure_all()
