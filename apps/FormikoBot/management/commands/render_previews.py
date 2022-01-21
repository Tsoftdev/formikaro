import os
import time
import sys
from pathlib import Path
from shutil import copyfile
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from django.conf import settings
import socket


#django librarys
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from datetime import datetime
from apps.ProductManager.models import Product, ProductBase, AE_STATUS_VALUE, PR_STATUS_VALUE, FO_STATUS_VALUE


SHOP_FOLDER = settings.SHOP_FOLDER #'/home/worker/Projects/mount/intake'
SHOP_SHELF_FOLDER = settings.SHOP_SHELF_FOLDER
SHOP_DEFAULT_ASSETS_FOLDER = settings.SHOP_DEFAULT_ASSETS_FOLDER
SHOP_ORDER_FOLDER = settings.SHOP_ORDER_FOLDER
SHOP_CLIENT_CI_FOLDER = settings.SHOP_CLIENT_CI_FOLDER
SHOP_DEFAULT_FOOTAGE_FOLDER = settings.SHOP_DEFAULT_FOOTAGE_FOLDER

SHOP_DEFAULT_PREVIEW_FOLDER = settings.SHOP_DEFAULT_PREVIEW_FOLDER
SHOP_ORDER_RENDER_FOLDER = settings.SHOP_ORDER_RENDER_FOLDER
SHOP_ORDER_RENDER_OUTPUT_FOLDER = settings.SHOP_ORDER_RENDER_OUTPUT_FOLDER
COPY_DELAY = settings.COPY_DELAY


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


class RenderPreviews:
    product_preview_path = ''
    
    def init_watchdog(self,path):
        self.stop = False
        self.watchpath = path
        patterns = "*"
        ignore_patterns = ""
        ignore_directories = False
        case_sensitive = True
        self.event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        self.event_handler.on_any_event = self.on_any_event
        self.event_handler.on_created = self.on_created
        self.observer = Observer()
        self.observer.schedule( self.event_handler, self.watchpath, recursive=False)
        self.observer.start()
    
    #on any event let's draw a dot so we see some action
    def on_any_event(self, event):
        print(".", end = "", flush=True)
        #print("SELF: %s " % self.product_preview_path)
        #print("any event [%s]" % event)
    
    def on_modified(self, event):
        print(f"hey buddy, {event.src_path} has been modified")
    
    #if a file has been created check if it's a FINAL one and secondly if it is an mp4 file
    #if yes copy it into the preview folder
    def on_created(self, event):
        new_file = str(os.path.basename(event.src_path))
        
        #print("FIND: ", new_file.find('FINAL', 0))
        filename, file_extension = os.path.splitext(event.src_path)
        
        #debug 20 to deactivate
        if new_file.find('FINAL', 0) >= 0:
            if file_extension == '.mp4':
                print("\n\t\t[CREATED] [%s]\t[%s]" % (new_file,event.src_path))
                self.stop = True
                print("\t\tFinished render:\t%s" % new_file)
                #so let's wait 5 seconds until its ready
                print("\t\tWaiting %s seconds" % COPY_DELAY)
                #time.sleep(int(COPY_DELAY))
                print("\t\tNow copying it to:\t%s" % self.product_preview_path)
            
                file_size = 0
                old_file_size = -1
                #print("[CHK]\t%s\t%s" % (old_file_size, file_size), flush=True) #DEBUG
                
                #this loop needs to be here so we wait until the file is completely written and not just copy a junk of it
                while file_size > old_file_size or file_size == 0:
                    old_file_size=file_size
                    file_size = Path(event.src_path).stat().st_size
                    #print("[CHK]\t%s\t%s" % (old_file_size, file_size), end='\n', flush=True) #DEBUG
                
                p = Path(self.product_preview_path)
                #if no preview folder exists, let's try to create one
                #print("see if p exists: [%s]" %  os.path.exists(p.parent))
                if not os.path.exists(p.parent):
                    try: 
                        os.makedirs(p.parent)
                    except IOError as e:
                        print("Unable to create preview folder. %s" % e)
                        exit(1)
                    except:
                        print("Unexpected error:", sys.exc_info())
                        exit(1)
                
                #first copy the file
                try: 
                    copyfile(event.src_path, self.product_preview_path)
                    #os.replace(event.src_path, self.product_preview_path)
                except IOError as e:
                    print("Unable to copy file (%s to %s). %s" % (event.src_path,self.product_preview_path, e))
                    exit(1)
                except:
                    print("Unexpected error:", sys.exc_info())
                    exit(1)
                
                #then delete the render file in the render folder
                #this is not working right now as it seems the file is either still locked by the system
                #or it's interrupting the copying. 
                #try: 
                #    os.remove(event.src_path)
                #except IOError as e:
                #    print("Unable to delete file (%s) %s" % (event.src_path, e))
                #    exit(1)
                #except:
                #    print("Unexpected error:", sys.exc_info())
                #    exit(1)
        
        #print(f"hey, {event.src_path} has been created!")
    
    def test2(self):
        print("OUTPUT: ", self.product_preview_path)
    
    def test(self):
        self.product_preview_path='gugu'
        self.test2()

    #here we take only the id of a product and derive everything from it
    #for now this is ONLY WORKING with a PRODUCT ID!!!
    def render_previews(self, product_id='', base=False, create=False):
    
        if base:
            try:
                this_product_base = ProductBase.objects.get(id=product_id)
                base_folder = this_product_base.get_folder()
            except:
                print("Could not find ProductBase (%s)" % product_id)
                return False
        elif product_id:
            try:
                this_product = Product.objects.get(id=product_id)
                folder = this_product.get_folder() 
                base_folder = this_product.base.get_folder()
            except:
                print("Could not find product (%s)" % product_id)
                return False
        else:
            print("Neither ProductBaseId or ProductId given. Aborting!")
            return False
    
        
        if not folder:
            return False
        
        print(">Checking folder: ", folder)
        if create:
            print(">Going to create previews")
        else: 
            print(">Just going to check")
        print("\n")
        
        weired_files = []
        comment = ''
        subfolders =[]
        
        #check base folder
        if not Path(folder).is_dir():
            print("File path [%s] does not exist!" % folder)
            return False
        
        #so we have the folder or the product now let's see what we have
        
        #check if FSIN.aep exists
        filename = this_product.get_project_file_name(False)
        product_filename = this_product.get_project_file_name(True)
        project_file = Path(folder) / product_filename
        if project_file.is_file():
            print("file exists: %s " % project_file)
            
        if this_product.base.mode != AE_STATUS_VALUE:
            print("Project is not an AfterEffects file, can't perform any render, sorry.")
            return False
        else:
            print("AfterEffects file found...")
        
            #product_filename = filename + file_extension
            product_preview_path = Path(base_folder) / SHOP_DEFAULT_PREVIEW_FOLDER / Path(filename + '.mp4')
            comment = '[After Effects Project]\n\t\t\t\t\t' 
            print("\t\tproduct:\t%s - \t%s" % (this_product, comment))
                            
            render_path = Path(SHOP_FOLDER) / SHOP_ORDER_RENDER_FOLDER / Path(product_filename)
            render_output_path = Path(SHOP_FOLDER) / SHOP_ORDER_RENDER_FOLDER / SHOP_ORDER_RENDER_OUTPUT_FOLDER
            print("\t\t[RENDER]")
                   
            #here we serve our file to the renderer in order to see if it's going to get rendered
            print("\t\tmove %s to %s" % (project_file, render_path))
            print("\t\twatch folder: \t%s" % render_output_path)
                            
            #this the name we are going to give our new preview:
            print("\t\tproduct_preview_path:\t%s" % product_preview_path)
                            
            if create:
                print("\t>Start rendering process...")
                self.product_preview_path = product_preview_path
                #set the watchpath
                start_time = time.time()
                self.watchpath = render_output_path
                            
                self.init_watchdog(render_output_path)
                #copy file this will trigger the render in the watched folder
                try: 
                    copyfile(project_file, render_path)
                except IOError as e:
                    print("Unable to copy file. %s" % e)
                    exit(1)
                except:
                    print("Unexpected error:", sys.exc_info())
                    exit(1)
                        
                print('\t\tRENDERING: ', end='')
                #now we wait until                            
                try:
                    while True and not self.stop:
                        time.sleep(3)
                
                except KeyboardInterrupt:
                    self.observer.stop()
                    self.observer.join()
                                    
                end_time = time.time()
                render_time = end_time - start_time
                this_product.rendertime = render_time
                host_name = socket.gethostname()
                this_product.write_log('Rendered preview. Time: %s on %s ' % (str(render_time), host_name)) #write log does the saving
                
                print("\tRENDER TIME: ", render_time)
        
        
        return True
        # THE CODE BELOW IS THE OLD DIRECTORY BASED APPROACH and depreciated
        # -------------------------------------------------------------------------
        
        # this is the directory based approach.. looking for what is really there.

        for item in os.listdir(folder):
            item_path = Path(folder) / item
            if os.path.isdir(item_path):
                if item == SHOP_DEFAULT_ASSETS_FOLDER:
                    print("\titem:\t%s\t\tfound ASSET folder" % item)
                    assets_path = Path(folder) / item
                    for asset in os.listdir(assets_path):
                        print("\t\t\tasset:\t\t%s" % asset)
                else:
                    print("\titem:\t%s\t\t(variety folder?)" % item)
                    variety_path = Path(folder) / item
                
                    for product in os.listdir(variety_path):
                        product_path = Path(variety_path) / product
                        filename, file_extension = os.path.splitext(product_path)
                        filename = str(os.path.basename(filename))

                        if file_extension == '.aep':
                            product_filename = filename + file_extension
                            product_preview_path = Path(folder) / SHOP_DEFAULT_PREVIEW_FOLDER / Path(filename + '.mp4')
                            comment = '[After Effects Project]\n\t\t\t\t\t' 
                            print("\t\tproduct:\t%s - %s\t%s" % (product, file_extension, comment))
                            
                            render_path = Path(SHOP_FOLDER) / SHOP_ORDER_RENDER_FOLDER / Path(product_filename)
                            render_output_path = Path(SHOP_FOLDER) / SHOP_ORDER_RENDER_FOLDER / SHOP_ORDER_RENDER_OUTPUT_FOLDER
                            print("\t\t[RENDER]")
                   
                            #here we serve our file to the renderer in order to see if it's going to get rendered
                            print("\t\tmove %s to %s" % (product_path, render_path))
                            print("\t\twatch folder: \t%s" % render_output_path)
                            
                            #this the name we are going to give our new preview:
                            print("\t\tproduct_preview_path:\t%s" % product_preview_path)
                            
                            if create:
                                print("\t>Start rendering process...")
                                self.product_preview_path = product_preview_path
                                #set the watchpath
                                start_time = time.time()
                                self.watchpath = render_output_path
                                
                                self.init_watchdog(render_output_path)
                                #copy file this will trigger the render in the watched folder
                                try: 
                                    copyfile(product_path, render_path)
                                except IOError as e:
                                    print("Unable to copy file. %s" % e)
                                    exit(1)
                                except:
                                    print("Unexpected error:", sys.exc_info())
                                    exit(1)
                            
                                print('\t\tRENDERING: ', end='')
                                #now we wait until                            
                                try:
                                    while True and not self.stop:
                                        time.sleep(3)
                                except KeyboardInterrupt:
                                    self.observer.stop()
                                    self.observer.join()
                                    
                                end_time = time.time()
                                render_time = end_time - start_time
                                print("\tRENDER TIME: ", render_time)
                       
                        elif file_extension == '.prproj':
                            comment = '[Premiere Project]'
                        else:
                            weired_files.append(Path(folder) / product)
            else:
                print("\t item:\t%s\t(whats that file?)" % item)
                weired_files.append(Path(folder) / item)
                
            #done with the evaluation
            #input = query_yes_no('Do you want to render preview files?')
            
            #if input:
            #    print(">rendering")
            #else:
            #    print(">NOT rendering")
            

        print("\n")
        print("Found (%s) weired files: \n" % len(weired_files))
        for file in weired_files:
            print("\t\t%s" % file)
        print("\n")
        # THE CODE ABOVE IS THE OLD DIRECTORY BASED APPROACH and depreciated
        # -------------------------------------------------------------------------
    

def testmy():
    file_size = 0
    old_file_size = -1
    path = Path('S:\WORKSHOP\SIMPLE\PREVIEW\test.txt')
    while file_size > old_file_size and file_size != 0:
        old_file_size=file_size
        file_size = Path(path).stat().st_size
        print("[CHK]\t%s\t%s" % (old_file_size, file_size), flush=True)
    
    
class Command(BaseCommand):
    help = 'Checks the availibility of usable product core files'

    def add_arguments(self, parser):
        parser.add_argument('--folder', action='append', type=str)
        parser.add_argument('--product', action='append', type=int)
        parser.add_argument('--productbase', action='append', type=int)
        parser.add_argument(
            '--create',
            action='store_true',
            help='This creates the folder structure for the base',
        )
        
    
    def handle(self, **options):
        
        if options['folder'] and options['product']:
            print("Folder _and_ product id are given. Please decide on either of them.")
            exit()
        
        #all other checks are performed in the function    
        
        rp = RenderPreviews()
        #rp.test()
        if options['product'] and options['productbase']:
            print("ProductBase _and_ product id are given. Please decide on either of them.")
            exit()  
        
        if options['product']:
            this_id = options['product'][0]
            base = False
        else:
            this_id = options['productbase'][0]
            base = True
        
        rp.render_previews(this_id, base, options['create'])
