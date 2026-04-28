import React, { useEffect, useState, useMemo } from 'react';
import { Cloud, CloudFog, CloudLightning, CloudRain, CloudSnow, Search, Sun, Moon } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

// --- API Functions ---
const fetchLocationByCoords = async (lat: number, lon: number) => {
  const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error("Failed to fetch location");
  return res.json();
};

const fetchLocationByCity = async (city: string) => {
  const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(city)}&format=json&limit=1`);
  if (!res.ok) throw new Error("Failed to search city");
  const data = await res.json();
  if (data.length === 0) throw new Error("City not found");
  return data[0];
};

const fetchWeather = async (lat: number, lon: number) => {
  const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,is_day,rain,snowfall,weather_code,wind_speed_10m,relative_humidity_2m&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5`);
  if (!res.ok) throw new Error("Failed to fetch weather");
  return res.json();
};

// --- Helpers ---
const getWeatherCondition = (code: number, isDay: number) => {
  if (code === 0) return isDay ? 'SUNNY' : 'CLEAR_NIGHT';
  if (code === 1 || code === 2) return 'PARTLY_CLOUDY';
  if (code === 3) return 'CLOUDY';
  if (code === 45 || code === 48) return 'FOG';
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return 'RAIN';
  if ([71, 73, 75, 85, 86].includes(code)) return 'SNOW';
  if ([95, 96, 99].includes(code)) return 'STORM';
  return 'UNKNOWN';
};

const getWeatherIcon = (condition: string, className?: string) => {
  switch (condition) {
    case 'SUNNY': return <Sun className={className} />;
    case 'CLEAR_NIGHT': return <Moon className={className} />;
    case 'PARTLY_CLOUDY': return <Cloud className={className} />;
    case 'CLOUDY': return <Cloud className={className} />;
    case 'FOG': return <CloudFog className={className} />;
    case 'RAIN': return <CloudRain className={className} />;
    case 'SNOW': return <CloudSnow className={className} />;
    case 'STORM': return <CloudLightning className={className} />;
    default: return <Sun className={className} />;
  }
};

const getDayName = (dateStr: string) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();
};

// --- Animations Components ---
const AnimationLayer = ({ condition }: { condition: string }) => {
  const elements = useMemo(() => {
    switch (condition) {
      case 'SUNNY':
        return (
          <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#ffaa0040] to-transparent">
            <div className="absolute top-[-50px] right-[-50px] w-[200px] h-[200px] bg-yellow-400 rounded-full blur-3xl opacity-50 animate-pulse"></div>
            <div className="absolute top-10 right-10 text-yellow-400 opacity-80">
              <Sun size={120} className="animate-spin-slow" style={{ animationDuration: '20s' }} />
            </div>
          </div>
        );
      case 'CLEAR_NIGHT':
        return (
          <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#1a0b2e] to-[#030206]">
            {Array.from({ length: 60 }).map((_, i) => (
              <div key={i} className="star" style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                width: `${Math.random() * 2 + 1}px`,
                height: `${Math.random() * 2 + 1}px`,
                '--duration': `${Math.random() * 3 + 1}s`,
                '--delay': `${Math.random() * 2}s`
              } as any} />
            ))}
            <div className="absolute top-10 right-10 text-blue-400 drop-shadow-[0_0_12px_rgba(0,136,255,0.8)]">
              <Moon size={80} />
            </div>
          </div>
        );
      case 'RAIN':
      case 'STORM':
        return (
          <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#0f172a] to-[#030206]">
            {Array.from({ length: 100 }).map((_, i) => (
              <div key={i} className="rain-streak" style={{
                left: `${Math.random() * 120 - 10}%`,
                '--speed': `${Math.random() * 0.4 + 0.4}s`,
                '--delay': `${Math.random() * 2}s`,
                '--length': `${Math.random() * 40 + 20}px`
              } as any} />
            ))}
            {condition === 'STORM' && <div className="lightning" />}
          </div>
        );
      case 'SNOW':
        return (
          <div className="absolute inset-0 overflow-hidden bg-[#030206]">
            {Array.from({ length: 70 }).map((_, i) => (
              <div key={i} className="snowflake" style={{
                left: `${Math.random() * 100}%`,
                '--speed': `${Math.random() * 4 + 3}s`,
                '--delay': `${Math.random() * 5}s`,
                '--size': `${Math.random() * 4 + 2}px`,
                '--drift-x': `${(Math.random() - 0.5) * 100}px`
              } as any} />
            ))}
          </div>
        );
      case 'CLOUDY':
      case 'PARTLY_CLOUDY':
        return (
          <div className="absolute inset-0 overflow-hidden bg-[#0a0a12]">
            {condition === 'PARTLY_CLOUDY' && (
              <div className="absolute top-10 right-10 text-yellow-400 opacity-60">
                <Sun size={80} />
              </div>
            )}
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="cloud" style={{
                top: `${Math.random() * 40}%`,
                width: `${Math.random() * 150 + 100}px`,
                height: `${Math.random() * 60 + 40}px`,
                '--speed': `${Math.random() * 20 + 20}s`,
                '--delay': `-${Math.random() * 20}s`
              } as any} />
            ))}
          </div>
        );
      case 'FOG':
        return (
          <div className="absolute inset-0 overflow-hidden bg-[#0a0a0f]">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="fog-band" style={{
                top: `${i * 12}%`,
                '--speed': `${Math.random() * 10 + 10}s`,
                '--delay': `-${Math.random() * 10}s`
              } as any} />
            ))}
          </div>
        );
      default:
        return <div className="absolute inset-0 bg-[#030206]" />;
    }
  }, [condition]);

  return elements;
};

// --- Main Component ---
export default function Weather() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [weatherData, setWeatherData] = useState<any>(null);
  const [locationName, setLocationName] = useState<string>("");
  const [cityInput, setCityInput] = useState("");
  const [needsLocation, setNeedsLocation] = useState(false);

  const loadData = async (lat: number, lon: number, name: string) => {
    try {
      setLoading(true);
      const data = await fetchWeather(lat, lon);
      setWeatherData(data);
      setLocationName(name);
      setNeedsLocation(false);
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to load weather data");
    } finally {
      setLoading(false);
    }
  };

  const initGeolocation = () => {
    setLoading(true);
    if (!navigator.geolocation) {
      setNeedsLocation(true);
      setLoading(false);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const loc = await fetchLocationByCoords(pos.coords.latitude, pos.coords.longitude);
          const name = loc.address?.city || loc.address?.town || loc.address?.village || "UNKNOWN_LOC";
          await loadData(pos.coords.latitude, pos.coords.longitude, name.toUpperCase());
        } catch (e) {
          setNeedsLocation(true);
          setLoading(false);
        }
      },
      () => {
        setNeedsLocation(true);
        setLoading(false);
      },
      { timeout: 4000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    initGeolocation();
    const interval = setInterval(() => {
      if (!needsLocation && weatherData) {
        initGeolocation(); // refresh
      }
    }, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCitySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cityInput.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const loc = await fetchLocationByCity(cityInput);
      const name = loc.name || cityInput;
      await loadData(parseFloat(loc.lat), parseFloat(loc.lon), name.toUpperCase());
    } catch (e: any) {
      setError(e.message || "City not found");
      setLoading(false);
    }
  };

  if (loading && !weatherData) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#030206] text-[#e8e0f5]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 border-4 border-[#ff00ff] border-t-transparent rounded-full animate-spin neon-box-primary"></div>
          <span className="font-mono text-xl neon-text-primary tracking-widest">INITIALIZING_SYS</span>
        </div>
      </div>
    );
  }

  if (needsLocation && !weatherData) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#030206] text-[#e8e0f5] p-4">
        <Card className="w-full max-w-sm bg-[#0a0a0f] border-[#cc00ff] p-6 neon-box-accent space-y-6">
          <div className="space-y-2 text-center">
            <h2 className="text-2xl font-bold font-mono neon-text-accent">LOCATION_REQ</h2>
            <p className="text-sm text-[#e8e0f5]/60 font-mono">Enter city to calibrate weather terminal.</p>
          </div>
          <form onSubmit={handleCitySearch} className="space-y-4">
            <Input 
              placeholder="e.g. DETROIT" 
              value={cityInput}
              onChange={(e) => setCityInput(e.target.value)}
              className="bg-[#030206] border-[#0088ff] text-[#e8e0f5] font-mono text-center tracking-widest focus-visible:ring-[#0088ff] focus-visible:ring-offset-0 neon-box-secondary"
            />
            <Button type="submit" disabled={loading} className="w-full bg-[#ff00ff] hover:bg-[#cc00ff] text-white font-mono font-bold tracking-widest">
              {loading ? "SCANNING..." : "CALIBRATE"}
            </Button>
            {error && <p className="text-[#ff5500] text-xs text-center font-mono neon-text-orange">{error}</p>}
          </form>
        </Card>
      </div>
    );
  }

  const current = weatherData.current;
  const daily = weatherData.daily;
  const condition = getWeatherCondition(current.weather_code, current.is_day);

  return (
    <div className={`relative h-[560px] w-[380px] overflow-hidden bg-[#030206] text-[#e8e0f5] font-mono mx-auto mt-10 rounded-xl border border-[#39ff14]/30 shadow-[0_0_20px_rgba(57,255,20,0.15)] ${condition === 'STORM' ? 'widget-shake' : ''}`}>
      {/* Background Animation Layer */}
      <AnimationLayer condition={condition} />

      {/* UI Overlay */}
      <div className="absolute inset-0 flex flex-col justify-between p-6 backdrop-blur-[2px]">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold tracking-tight neon-text-primary max-w-[200px] truncate">{locationName}</h1>
            <div className="mt-1 inline-flex items-center bg-[#0088ff]/20 border border-[#0088ff]/50 px-2 py-0.5 rounded text-xs neon-text-secondary">
              <span className="mr-2 uppercase">[{current.is_day ? 'DAY' : 'NIGHT'}]</span>
              SYS.ONLINE
            </div>
          </div>
          <div className="text-right">
            <Button variant="ghost" size="icon" onClick={() => setNeedsLocation(true)} className="h-8 w-8 hover:bg-[#ff00ff]/20 hover:text-[#ff00ff]">
              <Search className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Center Data */}
        <div className="flex flex-col items-center justify-center my-auto drop-shadow-md">
          <div className="text-7xl font-bold tracking-tighter neon-text-primary">
            {Math.round(current.temperature_2m)}°
          </div>
          <div className="text-lg text-[#e8e0f5]/80 mt-2">
            FEELS_LIKE: {Math.round(current.apparent_temperature)}°F
          </div>
          <div className="mt-4 px-4 py-1 border-2 border-[#39ff14] bg-[#39ff14]/10 text-[#39ff14] font-bold tracking-widest text-lg neon-box-green neon-text-green uppercase">
            {condition}
          </div>
        </div>

        {/* Small Stats */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-[#030206]/60 border border-[#ff5500]/50 rounded p-2 flex flex-col items-center backdrop-blur-sm neon-box-orange">
            <span className="text-[10px] text-[#e8e0f5]/60 mb-1">WIND_SPD</span>
            <span className="text-sm font-bold neon-text-orange">{current.wind_speed_10m} MPH</span>
          </div>
          <div className="bg-[#030206]/60 border border-[#0088ff]/50 rounded p-2 flex flex-col items-center backdrop-blur-sm neon-box-secondary">
            <span className="text-[10px] text-[#e8e0f5]/60 mb-1">HUMIDITY</span>
            <span className="text-sm font-bold neon-text-secondary">{current.relative_humidity_2m}%</span>
          </div>
        </div>

        {/* 5-Day Forecast */}
        <div className="bg-[#030206]/70 border border-[#cc00ff]/30 rounded-lg p-3 backdrop-blur-md">
          <div className="flex justify-between items-center text-xs mb-2 pb-2 border-b border-[#cc00ff]/20 text-[#cc00ff]">
            <span>FORECAST_5D</span>
            <span>TEMP_RANGE</span>
          </div>
          <div className="flex justify-between">
            {daily.time.slice(0, 5).map((date: string, i: number) => {
              const dayCondition = getWeatherCondition(daily.weather_code[i], 1);
              return (
                <div key={date} className="flex flex-col items-center gap-2">
                  <span className="text-xs font-bold text-[#e8e0f5]/80">{getDayName(date)}</span>
                  <div className="text-[#39ff14]">
                    {getWeatherIcon(dayCondition, "w-5 h-5")}
                  </div>
                  <div className="flex flex-col items-center text-[10px]">
                    <span className="text-[#ff00ff]">{Math.round(daily.temperature_2m_max[i])}°</span>
                    <span className="text-[#0088ff]">{Math.round(daily.temperature_2m_min[i])}°</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
