'use client';

interface AudioVisualizerProps {
  isActive: boolean;
  audioLevel: number; // 0-1
}

export function AudioVisualizer({ isActive, audioLevel }: AudioVisualizerProps) {
  return (
    <div
      className="flex items-end gap-1"
      role="img"
      aria-label={isActive ? `Audio visualizer active, level ${Math.round(audioLevel * 100)}%` : 'Audio visualizer inactive'}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className={`w-1 rounded-full bg-blue-500 ${isActive ? 'audio-bar' : ''
            }`}
          style={{
            height: isActive ? 'auto' : '0.25rem',
            animationDelay: `${i * 0.1}s`,
            opacity: audioLevel > 0 && isActive ? 1 : 0.7,
          }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
