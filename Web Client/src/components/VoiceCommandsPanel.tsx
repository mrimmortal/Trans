import { getVoiceCommandHelp } from "../services/voiceCommands";

export function VoiceCommandsPanel() {
  const commands = getVoiceCommandHelp();

  return (
    <div className="panel">
      <h2>Voice Commands</h2>
      <div className="vc-list">
        {commands.map((cmd) => (
          <div key={cmd.say} className="vc-row">
            <span className="vc-say">{cmd.say}</span>
            <span className="vc-arrow">&rarr;</span>
            <span className="vc-does">{cmd.does}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
