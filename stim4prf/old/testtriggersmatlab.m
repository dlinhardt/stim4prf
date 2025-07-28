ip = "169.254.197.24";
eye_connect(char(ip),5257);
eye_set_parameter('eye_save_tracking','true')
eye_set_software_event('test')
eye_set_parameter('eye_save_tracking','false')