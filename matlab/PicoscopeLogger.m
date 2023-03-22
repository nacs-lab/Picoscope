classdef PicoscopeLogger < handle
    properties
        ps; % Picoscope Object
        log_fname;
        log_fhdl = -1;
        
        log_chn_names = containers.Map();
        
    end
    methods (Access=private)
        function self = PicoscopeLogger(serial_str)
            self.ps = Picoscope.get(serial_str);
        end
    end
    methods
        function res = setFilename(self, filename)
            self.log_fname = filename;
            res = filename;
        end
        function self = setChn(self, chn_name, log_chn_name, coupling_type, maxV, offset)
            % chn_name is a string
            % log_chn_name is a string for the name to use for the log.
            % coupling_type is a string, either "dc" or "ac"
            % maxV will choose a voltage range that contains this value.
            % offset is an offset from 0 V
            self.ps.setChn(chn_name, coupling_type, maxV, offset);
            self.log_chn_names(chn_name) = log_chn_name;
        end
        function self = disableChn(self, chn_name)
            % chn_name is a string
            self.ps.disableChn(chn_name);
        end
        function self = setSimpleTrigger(self, chn_name, threshold, direction, delay, auto_trigger)
            % chn_name is a string
            % threshold is a threshold for the trigger in units of volts
            % direction is a string, ABOVE, BELOW, RISING, FALLING,
            % RISING_OR_FALLING
            % delay is in units of samples
            % auto_trigger is a timeout in ms. set to 0 to indefinitely
            % wait for trigger
            if ~exist('delay', 'var')
                delay = 0;
            end
            if ~exist('auto_trigger', 'var')
                auto_trigger = 1000; % default is 1 second timeout
            end
            self.ps.setSimpleTrigger(chn_name, threshold, direction, delay, auto_trigger);
        end
        function self = setTimeSettings(self, t_start, t_end, dt)
           % t_start is relative to trigger, so should be negative
           % t_end is relative to trigger, so should be positive. 
           % As far as I can tell, there's no way to have a "dead period"
           % after the trigger with no samples
           % dt is the resolution
           % all units are in seconds
            self.ps.setTimeSettings(t_start, t_end, dt);
        end
        function res = acquire(self, n_samples)
           % acquires samples based on previously set settings. 
           % and saves into file.
           if ~exist('n_samples', 'var')
                n_samples = 1;
           end
           first_write = 0;
            if self.log_fhdl == -1
               self.log_fhdl = fopen(self.log_fname, 'a');
               first_write = 1;
            end
           for i = 1:n_samples
               if mod(i, 10) == 1
                   fprintf("Acquiring %i\n", i);
               end
               currTime = clock;
                date_str = datestr(currTime, 'dd-mmm-yyyy HH:MM:SS:FFF');
                res = self.ps.acquire();
                if first_write
                    a = struct();
                    a.t_pts = res.time;
                    fprintf(self.log_fhdl, '%s\n', jsonencode(a));
                    first_write = 0;
                end
                toSave = struct();
                toSave.time = date_str;
                chn_name_keys = keys(self.log_chn_names);
                for j = 1:length(chn_name_keys)
                    this_key = chn_name_keys{j};
                    toSave.(self.log_chn_names(this_key)) = res.(this_key);
                end
                fprintf(self.log_fhdl, '%s\n', jsonencode(toSave));
           end
        end
        function res = closeFile(self)
            if self.log_fhdl >= 0
                fclose(self.log_fhdl);
                self.log_fhdl = -1;
            end
            self.log_fname = '';
            res = self;
        end
        function res = checkIfLog(self)
            res = self.log_fhdl >= 0;
        end
    end
    properties(Constant, Access=private)
        cache = containers.Map();
    end
    methods(Static)
        function dropAll()
            cache = PicoscopeLogger.cache;
            pic_keys = keys(cache);
            for i = 1:length(pic_keys)
                val = cache(pic_keys{i});
                val.closeFile();
            end
            remove(PicoscopeLogger.cache, keys(PicoscopeLogger.cache));
        end
        function res = get(ser_str)
            if ~exist('ser_str', 'var')
                error('Please input a string for the serial number.'); % Add support later.
            end
            if exist('ser_str', 'var')
                cache = PicoscopeLogger.cache;
                if isKey(cache, ser_str)
                    res = cache(ser_str);
                    if ~isempty(res) && isvalid(res)
                        return;
                    end
                end
                res = PicoscopeLogger(ser_str);
                cache(ser_str) = res;
            else
                res = PicoscopeLogger();
                cache(char(res.serial)) = res;
            end
        end
    end
end