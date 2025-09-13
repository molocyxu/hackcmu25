import os
import torch
from pyannote.audio import Pipeline
import argparse

def run_diarization(audio_file: str, output_file: str, hf_token: str):
    """
    Performs speaker diarization on an audio file and saves the result to a text file.

    Args:
        audio_file (str): Path to the input audio file.
        output_file (str): Path to save the output text file.
        hf_token (str): Your Hugging Face authentication token.
    """
    # 1. Check if the audio file exists
    if not os.path.exists(audio_file):
        print(f"❌ Error: Audio file not found at '{audio_file}'")
        return

    print("✅ Starting speaker diarization...")

    try:
        # 2. Load the pre-trained pipeline from Hugging Face
        print("   - Loading diarization model (this may take a moment)...")
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        # 3. Move the model to GPU if available for faster processing
        if torch.cuda.is_available():
            print("   - Moving model to GPU...")
            pipeline = pipeline.to("cuda")

        # 4. Run the diarization pipeline on the audio file
        print(f"   - Processing audio file: {os.path.basename(audio_file)}...")
        diarization = pipeline(audio_file)

        # 5. Format the results into a string
        result_str = "Speaker Diarization Results:\n"
        result_str += f"Source File: {os.path.basename(audio_file)}\n"
        result_str += "----------------------------------------\n"
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Format: [START_TIME -> END_TIME] Speaker_ID
            result_str += f"[{turn.start:04.1f}s -> {turn.end:04.1f}s] {speaker}\n"

        # 6. Write the formatted string to the output text file
        with open(output_file, "w") as f:
            f.write(result_str)

        print(f"✅ Diarization complete! Results saved to '{output_file}'")

    except Exception as e:
        print(f"❌ An error occurred during diarization: {e}")

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Perform speaker diarization on an audio file.")
    parser.add_argument("audio_file", type=str, help="Path to the input audio file (e.g., recording.wav).")
    parser.add_argument("hf_token", type=str, help="Your Hugging Face authentication token.")
    parser.add_argument("-o", "--output_file", type=str, default="diarization_result.txt", help="Path to the output text file (default: diarization_result.txt).")

    args = parser.parse_args()

    # Run the main function with the provided arguments
    run_diarization(args.audio_file, args.output_file, args.hf_token)
