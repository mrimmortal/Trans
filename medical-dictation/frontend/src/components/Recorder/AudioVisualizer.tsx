'use client';

import { useRef, useEffect } from 'react';

interface AudioVisualizerProps {
  isActive: boolean;
  audioLevel: number; // 0–1  (RMS from useAudioRecorder)
}

/**
 * Five vertical bars whose heights respond to the live audioLevel.
 *
 * ✅ FIXES:
 *   1. Old version set height:'auto' on empty divs → collapsed to 0px,
 *      relied on an `audio-bar` CSS class that may not exist.
 *   2. audioLevel was only used for opacity (binary 0.7 vs 1.0),
 *      so the bars never actually reflected loudness.
 *
 * Now each bar's height is computed from audioLevel with a per-bar
 * random jitter so they look like a real spectrum analyzer.  When
 * inactive, bars shrink to a 4px dot.  No external CSS class needed.
 */
export function AudioVisualizer({ isActive, audioLevel }: AudioVisualizerProps) {
  // Store random multipliers so each bar moves independently
  const jitterRef = useRef<number[]>([0.6, 1.0, 0.8, 0.9, 0.7]);

  // Refresh jitter values on each render while active so bars wiggle
  useEffect(() => {
    if (!isActive) return;

    let rafId: number;

    const tick = () => {
      jitterRef.current = jitterRef.current.map(
        () => 0.4 + Math.random() * 0.6 // range [0.4, 1.0]
      );
      rafId = requestAnimationFrame(tick);
    };

    // Throttle to ~15 fps to keep it lightweight
    const interval = setInterval(() => {
      rafId = requestAnimationFrame(tick);
    }, 67);

    return () => {
      clearInterval(interval);
      cancelAnimationFrame(rafId);
    };
  }, [isActive]);

  // Map audioLevel (0–1) to a pixel height per bar
  const MIN_BAR_H = 4;   // px when silent / inactive
  const MAX_BAR_H = 32;  // px at full volume

  return (
    <div
      className="flex items-end gap-[3px] h-8"
      role="img"
      aria-label={
        isActive
          ? `Audio visualizer active, level ${Math.round(audioLevel * 100)}%`
          : 'Audio visualizer inactive'
      }
    >
      {jitterRef.current.map((jitter, i) => {
        // Boost the RMS value so small sounds are still visible
        // RMS typically ranges 0–0.15 for normal speech, so we scale ×6
        const boosted = Math.min(audioLevel * 6, 1.0);
        const barH = isActive
          ? Math.max(MIN_BAR_H, boosted * jitter * MAX_BAR_H)
          : MIN_BAR_H;

        return (
          <div
            key={i}
            className="w-1 rounded-full transition-all duration-75"
            style={{
              height: `${barH}px`,
              backgroundColor: isActive
                ? boosted > 0.6
                  ? '#ef4444'  // red when loud
                  : boosted > 0.3
                    ? '#f59e0b' // amber mid-range
                    : '#3b82f6' // blue quiet
                : '#d1d5db',   // gray when off
              opacity: isActive ? 1 : 0.5,
            }}
            aria-hidden="true"
          />
        );
      })}
    </div>
  );
}