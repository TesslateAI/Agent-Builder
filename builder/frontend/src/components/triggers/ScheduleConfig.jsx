// components/triggers/ScheduleConfig.jsx
import React, { useCallback, useState, useEffect } from 'react';
import { Clock, Calendar, Play, Info } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';

const TIMEZONE_OPTIONS = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney'
];

const INTERVAL_UNITS = [
  { value: 'minutes', label: 'Minutes' },
  { value: 'hours', label: 'Hours' },
  { value: 'days', label: 'Days' },
  { value: 'weeks', label: 'Weeks' }
];

const CRON_PRESETS = [
  { label: 'Every minute', value: '* * * * *' },
  { label: 'Every 5 minutes', value: '*/5 * * * *' },
  { label: 'Every 15 minutes', value: '*/15 * * * *' },
  { label: 'Every 30 minutes', value: '*/30 * * * *' },
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Every 2 hours', value: '0 */2 * * *' },
  { label: 'Every 6 hours', value: '0 */6 * * *' },
  { label: 'Every 12 hours', value: '0 */12 * * *' },
  { label: 'Daily at midnight', value: '0 0 * * *' },
  { label: 'Daily at 9 AM', value: '0 9 * * *' },
  { label: 'Daily at 6 PM', value: '0 18 * * *' },
  { label: 'Weekly on Monday 9 AM', value: '0 9 * * 1' },
  { label: 'Monthly on 1st at midnight', value: '0 0 1 * *' },
  { label: 'Weekdays at 9 AM', value: '0 9 * * 1-5' },
  { label: 'Weekends at 10 AM', value: '0 10 * * 0,6' }
];

const ScheduleConfig = ({ config, onChange }) => {
  const [nextRuns, setNextRuns] = useState([]);
  const [cronError, setCronError] = useState('');

  const handleConfigChange = useCallback((field, value) => {
    const newConfig = {
      ...config,
      [field]: value
    };
    onChange(newConfig);
  }, [config, onChange]);

  const handleIntervalChange = useCallback((field, value) => {
    const newInterval = {
      ...config.interval,
      [field]: value
    };
    handleConfigChange('interval', newInterval);
  }, [config.interval, handleConfigChange]);

  // Generate next run preview
  const generateNextRuns = useCallback((scheduleConfig) => {
    // This is a simplified preview - in production you'd want a proper cron parser
    if (scheduleConfig.scheduleType === 'interval' && scheduleConfig.interval) {
      const { value, unit } = scheduleConfig.interval;
      if (!value || !unit) return [];

      const multiplier = {
        minutes: 60000,
        hours: 3600000,
        days: 86400000,
        weeks: 604800000
      }[unit];

      const now = new Date();
      const runs = [];
      for (let i = 1; i <= 5; i++) {
        runs.push(new Date(now.getTime() + (i * value * multiplier)));
      }
      return runs;
    }

    if (scheduleConfig.scheduleType === 'once' && scheduleConfig.oneTime) {
      return [new Date(scheduleConfig.oneTime)];
    }

    // For cron, we'd need a proper cron parser library
    return [];
  }, []);

  useEffect(() => {
    const runs = generateNextRuns(config);
    setNextRuns(runs);
  }, [config, generateNextRuns]);

  const formatDateTime = (date) => {
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: config.timezone || 'UTC'
    });
  };

  return (
    <div className="space-y-6">
      {/* Schedule Type */}
      <div className="space-y-2">
        <Label>Schedule Type</Label>
        <Select
          value={config.scheduleType || 'cron'}
          onValueChange={(value) => handleConfigChange('scheduleType', value)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="cron">Cron Expression</SelectItem>
            <SelectItem value="interval">Fixed Interval</SelectItem>
            <SelectItem value="once">One Time</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Timezone */}
      <div className="space-y-2">
        <Label>Timezone</Label>
        <Select
          value={config.timezone || 'UTC'}
          onValueChange={(value) => handleConfigChange('timezone', value)}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {TIMEZONE_OPTIONS.map(tz => (
              <SelectItem key={tz} value={tz}>{tz}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Separator />

      {/* Cron Configuration */}
      {config.scheduleType === 'cron' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-4 w-4" />
              <span>Cron Expression</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Quick Presets</Label>
              <div className="flex flex-wrap gap-2">
                {CRON_PRESETS.map(preset => (
                  <Button
                    key={preset.value}
                    variant="outline"
                    size="sm"
                    onClick={() => handleConfigChange('cronExpression', preset.value)}
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Cron Expression</Label>
              <Input
                value={config.cronExpression || ''}
                onChange={(e) => handleConfigChange('cronExpression', e.target.value)}
                placeholder="0 9 * * 1-5"
                className={cronError ? 'border-red-500' : ''}
              />
              {cronError && (
                <p className="text-xs text-red-600">{cronError}</p>
              )}
              <div className="text-xs text-gray-500">
                <p>Format: minute hour day month day_of_week</p>
                <p>Examples:</p>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li><code>0 9 * * *</code> - Every day at 9:00 AM</li>
                  <li><code>*/15 * * * *</code> - Every 15 minutes</li>
                  <li><code>0 9 * * 1-5</code> - Weekdays at 9:00 AM</li>
                  <li><code>0 0 1 * *</code> - First day of every month at midnight</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Interval Configuration */}
      {config.scheduleType === 'interval' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Play className="h-4 w-4" />
              <span>Fixed Interval</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Interval Value</Label>
                <Input
                  type="number"
                  min="1"
                  value={config.interval?.value || ''}
                  onChange={(e) => handleIntervalChange('value', parseInt(e.target.value) || 1)}
                  placeholder="1"
                />
              </div>
              <div className="space-y-2">
                <Label>Unit</Label>
                <Select
                  value={config.interval?.unit || 'hours'}
                  onValueChange={(value) => handleIntervalChange('unit', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {INTERVAL_UNITS.map(unit => (
                      <SelectItem key={unit.value} value={unit.value}>
                        {unit.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {config.interval?.value && config.interval?.unit && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  Trigger will run every {config.interval.value} {config.interval.unit}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* One Time Configuration */}
      {config.scheduleType === 'once' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Calendar className="h-4 w-4" />
              <span>One Time Execution</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Execution Date & Time</Label>
              <Input
                type="datetime-local"
                value={config.oneTime || ''}
                onChange={(e) => handleConfigChange('oneTime', e.target.value)}
              />
              <p className="text-xs text-gray-500">
                Time will be interpreted in the selected timezone: {config.timezone || 'UTC'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Start/End Dates */}
      <Card>
        <CardHeader>
          <CardTitle>Schedule Constraints (Optional)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                type="datetime-local"
                value={config.startDate || ''}
                onChange={(e) => handleConfigChange('startDate', e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>End Date</Label>
              <Input
                type="datetime-local"
                value={config.endDate || ''}
                onChange={(e) => handleConfigChange('endDate', e.target.value)}
              />
            </div>
          </div>
          <p className="text-xs text-gray-500">
            Leave empty for no constraints. Schedule will be active between these dates.
          </p>
        </CardContent>
      </Card>

      {/* Next Runs Preview */}
      {nextRuns.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Info className="h-4 w-4" />
              <span>Next Scheduled Runs</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {nextRuns.slice(0, 5).map((run, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm">{formatDateTime(run)}</span>
                  <Badge variant="outline" className="text-xs">
                    {index === 0 ? 'Next' : `+${index}`}
                  </Badge>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Preview times shown in {config.timezone || 'UTC'} timezone
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ScheduleConfig;