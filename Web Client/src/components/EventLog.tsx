import type { EventEntry } from "../hooks/useTranscriptionSession";

interface Props {
  events: EventEntry[];
}

const EVENT_COLORS: Record<string, string> = {
  connected: "green",
  disconnected: "gray",
  hello: "cyan",
  ready: "green",
  start_sent: "cyan",
  stop_sent: "amber",
  realtime: "cyan",
  final: "green",
  warning: "amber",
  error: "red",
  pong: "gray",
  metrics: "gray",
  clear: "amber",
  clear_sent: "amber",
  ws_error: "red",
  mic_error: "red",
  mic_permission_denied: "red",
  timeline: "gray",
  copy: "gray",
  export: "gray",
};

export function EventLog({ events }: Props) {
  return (
    <div className="panel event-panel">
      <h2>Event Log</h2>
      <div className="event-list">
        {events.length === 0 && (
          <div className="empty-events">No events yet</div>
        )}
        {events.map((event) => (
          <div key={event.id} className="event-row">
            <span className="event-time">
              {new Date(event.timestamp).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
            <span
              className={`event-type event-${EVENT_COLORS[event.type] ?? "gray"}`}
            >
              {event.type}
            </span>
            <span className="event-message">{event.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
