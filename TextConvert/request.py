from gradio_client import Client, file

client = Client("http://127.0.0.1:8010/")

async def get_voice(input_file_path: str):

    result = client.predict(
        enhance_resemble_chunk_seconds=8,
        enhance_resemble_chunk_overlap=1,
        enhance_resemble_solver="Midpoint",
        enhance_resemble_num_funcs=64,
        enhance_resemble_temperature=0.5,
        enhance_resemble_denoise=True,
        rvc_settings_model_path="",
        rvc_settings_index_path="",
        rvc_settings_model_name=None,
        rvc_settings_pitch=0,
        rvc_settings_index_rate=0.75,
        rvc_settings_protect_voiceless=0.33,
        rvc_settings_method="rmvpe",
        rvc_settings_filter_radius=3,
        rvc_settings_resemple_rate=0,
        rvc_settings_envelope_mix=1,
        opvoice_ref_list="None",
        batch_generation=[],
        batch_generation_path="",
        ref_speakers="",
        batch_sub_generation=[file(input_file_path)],
        batch_sub_generation_path="",
        sync_sub_generation=False,
        language_auto_detect=False,
        enable_waveform=False,
        improve_output_audio=False,
        improve_output_resemble=False,
        improve_output_voice2voice="None",
        output_type="mp3",
        text="",
        languages="Russian",
        speaker_value_text="RAY",
        speaker_path_text="",
        additional_text="output",
        temperature=0.75,
        length_penalty=1,
        repetition_penalty=5,
        top_k=50,
        top_p=0.85,
        speed=1,
        sentence_split=True,
        status_bar={"label":"Озвучка субтитров...","confidences":None},
        api_name="/generate_audio"
    )
    return result