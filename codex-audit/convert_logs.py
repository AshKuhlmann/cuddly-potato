import json
import os

def convert_log_file(input_path, output_path):
    """
    Converts a JSONL log file to a JSONL format suitable for fine-tuning.

    Args:
        input_path (str): The path to the input JSONL log file.
        output_path (str): The path to the output JSONL file.
    """
    # Clear the output file if it exists
    if os.path.exists(output_path):
        os.remove(output_path)

    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            try:
                turn = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping line in {input_path} due to JSONDecodeError")
                continue

            session_id = turn.get("session", {}).get("id")
            turn_id = turn.get("turn", {}).get("id")
            user_prompt = turn.get("messages", {}).get("user", [])
            assistant_response = turn.get("messages", {}).get("assistant", [])
            reasoning = turn.get("messages", {}).get("assistant_reasoning", [])
            
            tool_calls = []
            plan = []

            if "assistant_tool_calls" in turn:
                for tool_call in turn["assistant_tool_calls"]:
                    if tool_call.get("tool_name") == "update_plan":
                        plan.append(tool_call.get("arguments", {}).get("plan", []))
                    else:
                        tool_calls.append({
                            "tool_name": tool_call.get("tool_name"),
                            "arguments": tool_call.get("arguments"),
                            "output": tool_call.get("outputs", [])
                        })

            processed_turn = {
                "session_id": session_id,
                "turn_id": turn_id,
                "user_prompt": user_prompt,
                "assistant_response": assistant_response,
                "tool_calls": tool_calls,
                "reasoning": reasoning,
                "plan": plan
            }
            
            outfile.write(json.dumps(processed_turn) + '\n')

def main():
    """
    Main function to find and convert all source JSONL files.
    """
    source_files = [f for f in os.listdir('.') if f.endswith('.jsonl') and not f.startswith('tuning_')]
    
    if not source_files:
        print("No source .jsonl files found to convert.")
        return

    for source_file in source_files:
        output_file = f"tuning_{source_file}"
        print(f"Converting {source_file} to {output_file}...")
        convert_log_file(source_file, output_file)
    
    print("Conversion complete.")

if __name__ == "__main__":
    main()