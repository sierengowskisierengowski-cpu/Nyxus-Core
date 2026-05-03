import React, { useEffect, useState, useMemo } from 'react';
import { Cloud, CloudFog, CloudLightning, CloudRain, CloudSnow, Search, Sun, Moon, Wind, Droplets } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const fetchLocationByCoords = async (lat: number, lon: number) => {
  const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
  if (!res.ok) throw new Error('Failed to fetch location');
  return res.json();
};

const fetchLocationByCity = async (city: string) => {
  const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(city)}&format=json&limit=1`);
  if (!res.ok) throw new Error('Failed to search city');
  const data = await res.json();
  if (data.length === 0) throw new Error('City not found');
  return data[0];
};

const fetchWeather = async (lat: number, lon: number) => {
  const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,apparent_temperature,is_day,rain,snowfall,weather_code,wind_speed_10m,relative_humidity_2m&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5`);
  if (!res.ok) throw new Error('Failed to fetch weather');
  return res.json();
};

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

const getWeatherIcon = (condition: string, size = 32) => {
  const props = { size, strokeWidth: 1.5 };
  switch (condition) {
    case 'SUNNY':        return <Sun {...props} />;
    case 'CLEAR_NIGHT':  return <Moon {...props} />;
    case 'PARTLY_CLOUDY':return <Cloud {...props} />;
    case 'CLOUDY':       return <Cloud {...props} />;
    case 'FOG':          return <CloudFog {...props} />;
    case 'RAIN':         return <CloudRain {...props} />;
    case 'SNOW':         return <CloudSnow {...props} />;
    case 'STORM':        return <CloudLightning {...props} />;
    default:             return <Sun {...props} />;
  }
};

const conditionLabel = (condition: string) =>
  condition.replace(/_/g, ' ');

const getDayName = (dateStr: string) =>
  new Date(dateStr).toLocaleDateString('en-US', { weekday: 'short' }).toUpperCase();

const conditionColor: Record<string, string> = {
  SUNNY:         '#ffd700',
  CLEAR_NIGHT:   '#0088ff',
  PARTLY_CLOUDY: '#cc00ff',
  CLOUDY:        '#aaaacc',
  FOG:           '#8888aa',
  RAIN:          '#0088ff',
  SNOW:          '#00eeff',
  STORM:         '#ff5500',
  UNKNOWN:       '#ff00ff',
};

const AnimationLayer = ({ condition }: { condition: string }) =>
  useMemo(() => {
    switch (condition) {
      case 'SUNNY': return (
        <div className="absolute inset-0 overflow-hidden bg-gradient-to-br from-[#1a0900] via-[#08080e] to-[#08080e]">
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-yellow-400/10 rounded-full blur-3xl" />
          <div className="absolute top-8 right-12 text-yellow-400/60 drop-shadow-[0_0_40px_rgba(255,200,0,0.5)]">
            <Sun size={220} strokeWidth={0.8} style={{ animation: 'spin 40s linear infinite' }} />
          </div>
        </div>
      );
      case 'CLEAR_NIGHT': return (
        <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#04021a] via-[#08080e] to-[#08080e]">
          {Array.from({ length: 80 }).map((_, i) => (
            <div key={i} className="star" style={{
              left: `${Math.random() * 100}%`, top: `${Math.random() * 70}%`,
              width: `${Math.random() * 2 + 1}px`, height: `${Math.random() * 2 + 1}px`,
              '--duration': `${Math.random() * 3 + 1}s`, '--delay': `${Math.random() * 3}s`
            } as React.CSSProperties} />
          ))}
          <div className="absolute top-10 right-16 text-blue-300/60 drop-shadow-[0_0_30px_rgba(0,136,255,0.4)]">
            <Moon size={140} strokeWidth={0.8} />
          </div>
        </div>
      );
      case 'RAIN': return (
        <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#080c1a] to-[#08080e]">
          {Array.from({ length: 120 }).map((_, i) => (
            <div key={i} className="rain-streak" style={{
              left: `${Math.random() * 120 - 10}%`,
              '--speed': `${Math.random() * 0.4 + 0.4}s`,
              '--delay': `${Math.random() * 2}s`,
              '--length': `${Math.random() * 50 + 20}px`
            } as React.CSSProperties} />
          ))}
        </div>
      );
      case 'STORM': return (
        <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#0a0808] to-[#08080e]">
          {Array.from({ length: 120 }).map((_, i) => (
            <div key={i} className="rain-streak" style={{
              left: `${Math.random() * 120 - 10}%`,
              '--speed': `${Math.random() * 0.3 + 0.3}s`,
              '--delay': `${Math.random() * 2}s`,
              '--length': `${Math.random() * 60 + 30}px`
            } as React.CSSProperties} />
          ))}
          <div className="lightning" />
        </div>
      );
      case 'SNOW': return (
        <div className="absolute inset-0 overflow-hidden bg-gradient-to-b from-[#080e1a] to-[#08080e]">
          {Array.from({ length: 90 }).map((_, i) => (
            <div key={i} className="snowflake" style={{
              left: `${Math.random() * 100}%`,
              '--speed': `${Math.random() * 5 + 4}s`,
              '--delay': `${Math.random() * 6}s`,
              '--size': `${Math.random() * 5 + 2}px`,
              '--drift-x': `${(Math.random() - 0.5) * 120}px`
            } as React.CSSProperties} />
          ))}
        </div>
      );
      case 'CLOUDY':
      case 'PARTLY_CLOUDY': return (
        <div className="absolute inset-0 overflow-hidden bg-[#08080e]">
          {condition === 'PARTLY_CLOUDY' && (
            <div className="absolute top-10 right-12 text-yellow-400/40">
              <Sun size={160} strokeWidth={0.8} />
            </div>
          )}
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="cloud" style={{
              top: `${Math.random() * 50}%`,
              width: `${Math.random() * 250 + 120}px`,
              height: `${Math.random() * 80 + 50}px`,
              '--speed': `${Math.random() * 30 + 25}s`,
              '--delay': `-${Math.random() * 30}s`
            } as React.CSSProperties} />
          ))}
        </div>
      );
      case 'FOG': return (
        <div className="absolute inset-0 overflow-hidden bg-[#09090e]">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="fog-band" style={{
              top: `${i * 10}%`,
              '--speed': `${Math.random() * 12 + 12}s`,
              '--delay': `-${Math.random() * 12}s`
            } as React.CSSProperties} />
          ))}
        </div>
      );
      default: return <div className="absolute inset-0 bg-[#08080e]" />;
    }
  }, [condition]);

export default function Weather() {
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState<string | null>(null);
  const [weatherData, setWeatherData] = useState<any>(null);
  const [locationName, setLocationName] = useState('');
  const [cityInput, setCityInput]     = useState('');
  const [needsLocation, setNeedsLocation] = useState(false);
  const [showSearch, setShowSearch]   = useState(false);

  const loadData = async (lat: number, lon: number, name: string) => {
    try {
      setLoading(true);
      const data = await fetchWeather(lat, lon);
      setWeatherData(data);
      setLocationName(name);
      setNeedsLocation(false);
      setShowSearch(false);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Failed to load weather');
    } finally {
      setLoading(false);
    }
  };

  const initGeolocation = () => {
    setLoading(true);
    if (!navigator.geolocation) { setNeedsLocation(true); setLoading(false); return; }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const loc = await fetchLocationByCoords(pos.coords.latitude, pos.coords.longitude);
          const name = loc.address?.city || loc.address?.town || loc.address?.village || 'UNKNOWN';
          await loadData(pos.coords.latitude, pos.coords.longitude, name.toUpperCase());
        } catch { setNeedsLocation(true); setLoading(false); }
      },
      () => { setNeedsLocation(true); setLoading(false); },
      { timeout: 5000, maximumAge: 60000 }
    );
  };

  useEffect(() => {
    initGeolocation();
    const interval = setInterval(() => { if (!needsLocation && weatherData) initGeolocation(); }, 10 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleCitySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cityInput.trim()) return;
    try {
      setLoading(true); setError(null);
      const loc = await fetchLocationByCity(cityInput);
      await loadData(parseFloat(loc.lat), parseFloat(loc.lon), (loc.name || cityInput).toUpperCase());
    } catch (e: any) { setError(e.message || 'City not found'); setLoading(false); }
  };

  if (loading && !weatherData) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#08080e]">
        <div className="flex flex-col items-center gap-5">
          <div className="h-14 w-14 border-4 border-[#ff00ff] border-t-transparent rounded-full animate-spin" style={{ boxShadow: '0 0 20px #ff00ff88' }} />
          <span style={{ fontFamily: "'Caveat',cursive", fontSize: 28, color: '#ff00ff', textShadow: '0 0 12px #ff00ff' }}>
            LOADING WEATHER...
          </span>
        </div>
      </div>
    );
  }

  if ((needsLocation && !weatherData) || showSearch) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-[#08080e] text-white">
        <div style={{
          width: 380, background: '#0d0d1a',
          border: '2px solid #cc00ff', borderRadius: 16, padding: 32,
          boxShadow: '0 0 40px #cc00ff44',
        }}>
          <h2 style={{ fontFamily: "'Caveat',cursive", fontSize: 36, color: '#cc00ff', textShadow: '0 0 12px #cc00ff', marginBottom: 8, textAlign: 'center' }}>
            LOCATION
          </h2>
          <p style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12, color: 'rgba(255,255,255,0.4)', textAlign: 'center', marginBottom: 24, letterSpacing: '0.1em' }}>
            ENTER CITY TO CALIBRATE WEATHER TERMINAL
          </p>
          <form onSubmit={handleCitySearch} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Input
              placeholder="e.g. DETROIT"
              value={cityInput}
              onChange={e => setCityInput(e.target.value)}
              style={{ background: '#030206', border: '1px solid #0088ff', color: '#e8e0f5', fontFamily: "'JetBrains Mono',monospace", textAlign: 'center', letterSpacing: '0.2em', boxShadow: '0 0 10px #0088ff44' }}
            />
            <Button type="submit" disabled={loading} style={{ background: '#ff00ff', color: '#000', fontFamily: "'Caveat',cursive", fontSize: 20, fontWeight: 700, letterSpacing: '0.1em', boxShadow: '0 0 14px #ff00ff66' }}>
              {loading ? 'SCANNING...' : 'CALIBRATE'}
            </Button>
            {weatherData && (
              <button type="button" onClick={() => setShowSearch(false)} style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, fontFamily: "'JetBrains Mono',monospace", background: 'none', border: 'none', cursor: 'pointer' }}>
                ← BACK
              </button>
            )}
            {error && <p style={{ color: '#ff5500', fontSize: 12, textAlign: 'center', fontFamily: "'JetBrains Mono',monospace" }}>{error}</p>}
          </form>
        </div>
      </div>
    );
  }

  const current   = weatherData.current;
  const daily     = weatherData.daily;
  const condition = getWeatherCondition(current.weather_code, current.is_day);
  const color     = conditionColor[condition] ?? '#ff00ff';
  const temp      = Math.round(current.temperature_2m);
  const feels     = Math.round(current.apparent_temperature);
  const wind      = Math.round(current.wind_speed_10m);
  const humidity  = current.relative_humidity_2m;
  const precip0   = daily.precipitation_probability_max?.[0] ?? 0;

  return (
    <div className={`relative h-screen w-screen overflow-hidden bg-[#08080e] text-white ${condition === 'STORM' ? 'widget-shake' : ''}`}>
      <AnimationLayer condition={condition} />

      {/* Gradient overlay for readability */}
      <div className="absolute inset-0" style={{
        background: 'linear-gradient(105deg, rgba(0,0,0,0.82) 0%, rgba(0,0,0,0.55) 50%, rgba(0,0,0,0.22) 100%)',
      }} />

      {/* Content grid */}
      <div className="absolute inset-0 flex" style={{ padding: '32px 40px' }}>

        {/* ── LEFT: Current weather ───────────────────────────── */}
        <div style={{ width: '42%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>

          {/* Header */}
          <div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.3em', textTransform: 'uppercase', marginBottom: 4 }}>
              NYXUS WEATHER TERMINAL
            </div>
            <div style={{ fontFamily: "'Caveat',cursive", fontSize: 52, fontWeight: 700, color, textShadow: `0 0 20px ${color}88`, lineHeight: 1.05, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {locationName}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8 }}>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, letterSpacing: '0.25em', padding: '2px 8px', background: `${color}22`, border: `1px solid ${color}55`, borderRadius: 4, color }}>
                [{current.is_day ? 'DAY' : 'NIGHT'}]
              </span>
              <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.15em' }}>
                SYS.ONLINE
              </span>
              <button
                onClick={() => setShowSearch(true)}
                style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 6, padding: '4px 10px', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, transition: 'all 0.2s' }}
                onMouseEnter={e => (e.currentTarget.style.color = '#fff')}
                onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.5)')}
              >
                <Search size={13} />
              </button>
            </div>
          </div>

          {/* Big temperature */}
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 4 }}>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 'clamp(90px,12vw,160px)', fontWeight: 800, lineHeight: 0.9, color, textShadow: `0 0 30px ${color}66` }}>
                {temp}
              </span>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 40, fontWeight: 600, marginTop: 16, color: 'rgba(255,255,255,0.6)' }}>°F</span>
            </div>
            <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 14, color: 'rgba(255,255,255,0.5)', marginTop: 6, letterSpacing: '0.05em' }}>
              Feels like {feels}°F
            </div>

            {/* Condition badge */}
            <div style={{ marginTop: 20, display: 'inline-flex', alignItems: 'center', gap: 12, padding: '8px 20px', background: `${color}15`, border: `2px solid ${color}55`, borderRadius: 10, boxShadow: `0 0 16px ${color}33` }}>
              <span style={{ color, opacity: 0.9 }}>{getWeatherIcon(condition, 28)}</span>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 28, fontWeight: 700, color, textShadow: `0 0 10px ${color}` }}>
                {conditionLabel(condition)}
              </span>
            </div>
          </div>

          {/* Stats */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div style={{ padding: '16px 18px', background: 'rgba(0,0,0,0.45)', border: '1px solid rgba(255,85,0,0.35)', borderRadius: 12, backdropFilter: 'blur(14px) saturate(1.6)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Wind size={13} color="rgba(255,255,255,0.3)" />
                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.25em' }}>WIND SPEED</span>
              </div>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 30, fontWeight: 700, color: '#ff5500', textShadow: '0 0 10px #ff550088' }}>
                {wind} <span style={{ fontSize: 16, fontWeight: 500 }}>MPH</span>
              </span>
            </div>
            <div style={{ padding: '16px 18px', background: 'rgba(0,0,0,0.45)', border: '1px solid rgba(0,136,255,0.35)', borderRadius: 12, backdropFilter: 'blur(14px) saturate(1.6)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <Droplets size={13} color="rgba(255,255,255,0.3)" />
                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.25em' }}>HUMIDITY</span>
              </div>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 30, fontWeight: 700, color: '#0088ff', textShadow: '0 0 10px #0088ff88' }}>
                {humidity}<span style={{ fontSize: 16, fontWeight: 500 }}>%</span>
              </span>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Forecast ─────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingLeft: 40 }}>

          <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.3em', textTransform: 'uppercase', marginBottom: 16 }}>
            5-DAY FORECAST
          </div>

          {/* Forecast cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
            {daily.time.slice(0, 5).map((date: string, i: number) => {
              const dc      = getWeatherCondition(daily.weather_code[i], 1);
              const dc_col  = conditionColor[dc] ?? '#ff00ff';
              const isToday = i === 0;
              const precip  = daily.precipitation_probability_max?.[i] ?? 0;
              return (
                <div key={date} style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10,
                  padding: '18px 8px',
                  background: isToday ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.38)',
                  border: isToday ? `2px solid ${color}55` : '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 16, backdropFilter: 'blur(14px) saturate(1.6)',
                  boxShadow: isToday ? `0 0 20px ${color}22` : 'none',
                  transition: 'all 0.2s',
                }}>
                  <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, fontWeight: 700, letterSpacing: '0.2em', color: isToday ? color : 'rgba(255,255,255,0.5)' }}>
                    {isToday ? 'TODAY' : getDayName(date)}
                  </span>
                  <span style={{ color: isToday ? dc_col : 'rgba(255,255,255,0.6)' }}>
                    {getWeatherIcon(dc, 26)}
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <span style={{ fontFamily: "'Caveat',cursive", fontSize: 22, fontWeight: 700, color: '#ff00ff', textShadow: '0 0 8px #ff00ff66' }}>
                      {Math.round(daily.temperature_2m_max[i])}°
                    </span>
                    <span style={{ fontFamily: "'Caveat',cursive", fontSize: 17, color: '#0088ff' }}>
                      {Math.round(daily.temperature_2m_min[i])}°
                    </span>
                  </div>
                  {precip > 0 && (
                    <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 8, color: '#0088ff', letterSpacing: '0.1em' }}>
                      ▼ {precip}%
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          {/* Precipitation bar */}
          {precip0 > 0 && (
            <div style={{ marginTop: 20, padding: '16px 20px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(0,136,255,0.2)', borderRadius: 12, backdropFilter: 'blur(14px) saturate(1.6)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: 'rgba(255,255,255,0.35)', letterSpacing: '0.25em' }}>PRECIP CHANCE TODAY</span>
                <span style={{ fontFamily: "'Caveat',cursive", fontSize: 18, fontWeight: 700, color: '#0088ff' }}>{precip0}%</span>
              </div>
              <div style={{ height: 5, background: 'rgba(255,255,255,0.08)', borderRadius: 99, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${precip0}%`, background: 'linear-gradient(90deg, #0088ff, #cc00ff)', borderRadius: 99, transition: 'width 1s ease' }} />
              </div>
            </div>
          )}

          {/* UV / Visibility extra row */}
          <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(57,255,20,0.2)', borderRadius: 12, backdropFilter: 'blur(14px) saturate(1.6)' }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.2em', marginBottom: 4 }}>MAX TEMP</div>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 24, fontWeight: 700, color: '#39ff14', textShadow: '0 0 8px #39ff1466' }}>
                {Math.round(daily.temperature_2m_max[0])}°F
              </span>
            </div>
            <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(204,0,255,0.2)', borderRadius: 12, backdropFilter: 'blur(14px) saturate(1.6)' }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 9, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.2em', marginBottom: 4 }}>MIN TEMP</div>
              <span style={{ fontFamily: "'Caveat',cursive", fontSize: 24, fontWeight: 700, color: '#cc00ff', textShadow: '0 0 8px #cc00ff66' }}>
                {Math.round(daily.temperature_2m_min[0])}°F
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* NYX stamp */}
      <div style={{
        position: 'absolute', bottom: 6, right: 10,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 7, letterSpacing: '0.18em',
        color: 'rgba(255,255,255,0.12)',
        pointerEvents: 'none', zIndex: 50,
        whiteSpace: 'nowrap',
      }}>
        © 2026 NYX-J5W-2026-SIERENGOWSKI-LOCKED
      </div>
    </div>
  );
}
