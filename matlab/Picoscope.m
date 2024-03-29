%% wrapper for Picoscope.py

classdef Picoscope < handle
    properties
        ps;
        serial;
        triggerSet;
        % configuration for time, samples to capture.
        configured;
        preTrigSamples;
        postTrigSamples;
        timebase;
        interval_ns;
    end

    methods(Access = private)
        function self = Picoscope(serial_str)
            [path, ~, ~] = fileparts(mfilename('fullpath'));
            path = [path, '\..\'];
            if exist('serial_str', 'var')
                pyglob = py.dict(pyargs('mat_srcpath', path, 'serial', serial_str));
            else
                pyglob = py.dict(pyargs('mat_srcpath', path));
            end
            try
                py.exec('from libps import Picoscope', pyglob);
            catch
                py.exec('import sys; sys.path.append(mat_srcpath)', pyglob);
                py.exec('from libps import Picoscope', pyglob);
            end
            if exist('serial_str', 'var')
                self.ps = py.eval('Picoscope.Picoscope(serial)', pyglob);
            else
                self.ps = py.eval('Picoscope.Picoscope()', pyglob);
            end
            self.serial = char(uint8(self.ps.serial));
            self.configured = 0;
            self.triggerSet = 0;
        end
    end
    methods
        function self = setChn(self, chn_name, coupling_type, maxV, offset)
            % chn_name is a string
            % coupling_type is a string, either "dc" or "ac"
            % maxV will choose a voltage range that contains this value.
            % offset is an offset from 0 V
            self.ps.setChn(chn_name, true, coupling_type, maxV, offset);
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
            self.ps.setSimpleTrigger(chn_name, threshold, direction, py.int(delay), py.int(auto_trigger));
            self.triggerSet = 1;
        end
        function self = setTimeSettings(self, t_start, t_end, dt)
           % t_start is relative to trigger, so should be negative
           % t_end is relative to trigger, so should be positive. 
           % As far as I can tell, there's no way to have a "dead period"
           % after the trigger with no samples
           % dt is the resolution
           % all units are in seconds
           res = cell(self.ps.getSamplesToCapture(t_start, t_end, dt));
           self.preTrigSamples = res{1};
           self.postTrigSamples = res{2};
           self.timebase = res{3};
           self.interval_ns = res{4};
           self.configured = 1;
        end
        function res = acquire(self)
           % acquires samples based on previously set settings. 
           % do best to error check
           if ~self.triggerSet
                error('Please specify the trigger settings with setSimpleTrigger');
           end
           if ~self.configured
               error('Plesae configure the time settings with setTimeSettings');
           end
           raw = struct(self.ps.acquireBlock(self.preTrigSamples, self.postTrigSamples, self.timebase, self.interval_ns));
           fnames = fieldnames(raw);
           res = struct();
           for i = 1:length(fnames)
               this_name = fnames{i};
               res.(this_name) = cellfun(@double, cell(raw.(this_name)));
           end
        end
    end

    properties(Constant, Access=private)
        cache = containers.Map();
    end
    methods(Static)
        function dropAll()
            cache = Picoscope.cache;
            pic_keys = keys(cache);
            for i = 1:length(pic_keys)
                val = cache(pic_keys{i});
                val.ps = [];
            end
            remove(Picoscope.cache, keys(Picoscope.cache));
        end
        function res = get(ser_str)
            if ~exist('ser_str', 'var')
                error('Please input a string for the serial number.'); % Add support later.
            end
            if exist('ser_str', 'var')
                cache = Picoscope.cache;
                if isKey(cache, ser_str)
                    res = cache(ser_str);
                    if ~isempty(res) && isvalid(res)
                        return;
                    end
                end
                res = Picoscope(ser_str);
                cache(ser_str) = res;
            else
                res = Picoscope();
                cache(char(res.serial)) = res;
            end
        end
    end
end