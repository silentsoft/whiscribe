import multiprocessing
import subprocess
from datetime import datetime
import asyncio
import os
import sys
import stat
import flet as ft
from whisper import tokenizer

from whiscribe.transcriber import Transcriber
from whiscribe.audio import get_audio_tracks, extract_audio_track
from whiscribe.srt import convert_segments_to_srt
from whiscribe.version import version
from whiscribe.logo import svg_logo
from whiscribe.hits import count_launch, count_transcribe


BG_COLOR = "#0B0D17"  # Deep space dark background
SURFACE_COLOR = "#151821"  # Slightly lighter for panels/sidebar
CARD_COLOR = "#1A1C28"  # For elevated cards/inputs
TEXT_PRIMARY = "#F3F4F6"
TEXT_SECONDARY = "#9CA3AF"
BORDER_COLOR = "#2D334D"
ACCENT_PRIMARY = "#6366F1"  # Indigo


async def main(page: ft.Page):
    page.title = "Whiscribe"
    if sys.platform.startswith("darwin"):
        page.window.title_bar_hidden = True
    page.window.title_bar_buttons_hidden = False
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_COLOR
    page.window.width = 800
    page.window.height = 600
    page.window_resizable = True
    page.padding = 0
    page.spacing = 0
    page.fonts = {
        "Inter": "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Regular.woff2",
        "Inter-Medium": "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-Medium.woff2",
        "Inter-SemiBold": "https://raw.githubusercontent.com/rsms/inter/master/docs/font-files/Inter-SemiBold.woff2",
    }
    page.theme = ft.Theme(font_family="Inter")

    state = {
        "selected_file_path": None,
        "extracted_tracks": [],
        "current_audio_path": None,
        "transcriber": None,
        "srt_content": ""
    }

    def show_message(message):
        page.show_dialog(
            ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_600)
        )

    def show_error(message):
        page.show_dialog(
            ft.SnackBar(ft.Text(message, color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_800)
        )

    # 1. Sidebar Components
    model_dropdown = ft.Dropdown(
        label="Model",
        options=[ft.DropdownOption(key=m, text=m) for m in ["tiny", "base", "small", "medium", "large", "turbo"]],
        value="turbo",
        expand=True,
        border_color=BORDER_COLOR,
        bgcolor="#0E1018",
        focused_border_color=ACCENT_PRIMARY,
        border_radius=10,
        content_padding=15,
        text_size=13,
        label_style=ft.TextStyle(color=TEXT_SECONDARY)
    )

    system_locales = (await page.get_device_info()).locales
    system_language_code = system_locales[0].language_code if system_locales else "en"
    if system_language_code not in tokenizer.LANGUAGES:
        system_language_code = "en"

    language_dropdown = ft.Dropdown(
        label="Language",
        options=[ft.DropdownOption(key=code, text=name) for code, name in tokenizer.LANGUAGES.items()],
        value=system_language_code,
        expand=True,
        border_color=BORDER_COLOR,
        bgcolor="#0E1018",
        focused_border_color=ACCENT_PRIMARY,
        border_radius=10,
        content_padding=15,
        text_size=13,
        label_style=ft.TextStyle(color=TEXT_SECONDARY)
    )

    # 2. Main Components
    file_name_text = ft.Text("Browse to transcribe", size=14, color=TEXT_SECONDARY,
                             font_family="Inter-Medium")
    file_icon = ft.Icon(ft.Icons.VIDEO_FILE, size=48, color=TEXT_SECONDARY)

    async def handle_pick_files(e):
        files = await ft.FilePicker().pick_files(allow_multiple=False)
        if files:
            state["selected_file_path"] = files[0].path

            # Update Dropzone UI
            file_icon.icon = ft.Icons.AUDIO_FILE
            file_icon.color = ACCENT_PRIMARY
            file_name_text.value = f"{os.path.basename(state['selected_file_path'])}"
            file_name_text.color = TEXT_PRIMARY
            dropzone_card.border = ft.Border.all(1, "#373E59")
            dropzone_card.bgcolor = SURFACE_COLOR
            dropzone_card.shadow = ft.BoxShadow(spread_radius=1, blur_radius=25,
                                                color=ft.Colors.with_opacity(0.08, ACCENT_PRIMARY))

            # Reset Result UI
            track_dropdown.visible = False
            srt_editor.value = "Transcription will appear here."
            save_button.visible = False
            transcribe_button.disabled = True
            post_selection_area.visible = True
            
            # Show loading state on browse button
            browse_button.disabled = True
            browse_button.content = ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=TEXT_PRIMARY),
                ft.Text("Processing...", size=14, font_family="Inter-Medium", color=TEXT_PRIMARY)
            ], alignment=ft.MainAxisAlignment.CENTER)
            browse_button.style.mouse_cursor = ft.MouseCursor.NO_DROP
            page.update()

            # Extract Tracks
            try:
                loop = asyncio.get_event_loop()
                audio_tracks = await loop.run_in_executor(None, lambda: get_audio_tracks(state["selected_file_path"]))
                if audio_tracks:
                    extracted = []
                    for i, track in enumerate(audio_tracks):
                        path = await loop.run_in_executor(None, lambda i=i: extract_audio_track(state["selected_file_path"], i))
                        extracted.append((track, path))
                    state["extracted_tracks"] = extracted

                    track_dropdown.options = [
                        ft.DropdownOption(key=str(i), text=f"Track {i + 1} ({track.get('codec_name', 'audio')})")
                        for i, (track, _) in enumerate(extracted)
                    ]
                    track_dropdown.value = "0"
                    track_dropdown.visible = True

                    state["current_audio_path"] = state["extracted_tracks"][0][1]
                    transcribe_button.disabled = False
                else:
                    show_error("No audio tracks found!")
            except Exception as ex:
                show_error(f"Error: {str(ex)}")
            finally:
                # Restore browse button state
                browse_button.disabled = False
                browse_button.content = ft.Row([
                    ft.Icon(ft.Icons.FOLDER_OPEN, color=TEXT_PRIMARY, size=18),
                    ft.Text("Browse File", size=14, font_family="Inter-Medium", color=TEXT_PRIMARY)
                ], alignment=ft.MainAxisAlignment.CENTER)
                browse_button.style.mouse_cursor = ft.MouseCursor.CLICK
                page.update()

    browse_button = ft.Button(
        content=ft.Row([
            ft.Icon(ft.Icons.FOLDER_OPEN, color=TEXT_PRIMARY, size=18),
            ft.Text("Browse File", size=14, font_family="Inter-Medium", color=TEXT_PRIMARY)
        ], alignment=ft.MainAxisAlignment.CENTER),
        width=165,
        style=ft.ButtonStyle(
            color=TEXT_PRIMARY,
            bgcolor="#24283B",
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            mouse_cursor=ft.MouseCursor.CLICK
        ),
        on_click=handle_pick_files
    )

    dropzone_card = ft.Container(
        content=ft.Column([
            file_icon,
            file_name_text,
            browse_button
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
        height=160,
        border_radius=20
    )

    async def handle_track_change(e):
        idx = int(track_dropdown.value)
        state["current_audio_path"] = state["extracted_tracks"][idx][1]
        page.update()

    track_dropdown = ft.Dropdown(
        label="Audio Track",
        options=[],
        visible=False,
        expand=True,
        border_color=BORDER_COLOR,
        bgcolor=CARD_COLOR,
        focused_border_color=ACCENT_PRIMARY,
        border_radius=10,
        content_padding=15,
        text_size=13,
        on_select=handle_track_change
    )

    hints_input = ft.TextField(
        label="Word Hints",
        hint_text="Comma separated proper noun words, technical terms, acronyms, etc.",
        border_color=BORDER_COLOR,
        bgcolor=CARD_COLOR,
        focused_border_color=ACCENT_PRIMARY,
        border_radius=10,
        content_padding=15,
        text_size=13,
    )

    srt_editor = ft.TextField(
        multiline=True,
        border_color=ft.Colors.TRANSPARENT,
        bgcolor="#0A0B10",  # Very dark terminal feel
        expand=True,
        visible=True,
        read_only=True,
        value="Transcription will appear here.",
        color=TEXT_PRIMARY,
        border_radius=10,
        content_padding=15,
        text_size=13,
    )

    async def handle_save_file(e):
        if not state["srt_content"]: return
        file_name, extension = os.path.splitext(os.path.basename(state["selected_file_path"]))
        save_path = await ft.FilePicker().save_file(
            file_name=f"{file_name}",
            allowed_extensions=["srt"],
            initial_directory=os.path.dirname(file_name)
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(srt_editor.value)
            show_message(f"Successfully saved to {save_path}")

    save_button = ft.Button(
        content=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.DOWNLOAD_ROUNDED, color=TEXT_PRIMARY, size=18),
                ft.Text("Save As", size=14, font_family="Inter-SemiBold", color=TEXT_PRIMARY)
            ], alignment=ft.MainAxisAlignment.CENTER),
            alignment=ft.Alignment.CENTER,
        ),
        expand=True,
        style=ft.ButtonStyle(
            bgcolor=SURFACE_COLOR,
            color=TEXT_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            mouse_cursor=ft.MouseCursor.CLICK,
        ),
        visible=False,
        on_click=handle_save_file
    )

    async def run_transcription(e):
        model_size = model_dropdown.value
        language_code = language_dropdown.value
        hints = [h.strip() for h in hints_input.value.strip().split(",") if h.strip()]
        prompt = ", ".join(hints) if hints else None

        transcribe_button.disabled = True
        transcribe_button.content.content = ft.Row([
            ft.ProgressRing(width=16, height=16, stroke_width=2, color=ft.Colors.WHITE),
            ft.Text("Transcribing...", size=14, font_family="Inter-SemiBold", color=ft.Colors.WHITE)
        ], alignment=ft.MainAxisAlignment.CENTER)
        transcribe_button.style.mouse_cursor = ft.MouseCursor.NO_DROP
        srt_editor.value = "Generating subtitles... This may take a while."
        srt_editor.read_only = True
        page.update()

        try:
            loop = asyncio.get_event_loop()

            if not state["transcriber"] or state.get("last_model") != model_size:
                # Load model in background to prevent UI freeze
                state["transcriber"] = await loop.run_in_executor(None, lambda: Transcriber(model_size))
                state["last_model"] = model_size

            segments = await loop.run_in_executor(
                None,
                lambda: state["transcriber"].transcribe(
                    state["current_audio_path"],
                    language=language_code,
                    initial_prompt=prompt
                )
            )

            state["srt_content"] = convert_segments_to_srt(segments)
            srt_editor.value = state["srt_content"]
            srt_editor.read_only = False
            save_button.visible = True

            show_message("Transcription Completed!")
            count_transcribe()
        except Exception as ex:
            show_error(f"Error: {str(ex)}")
        finally:
            transcribe_button.disabled = False
            transcribe_button.content.content = ft.Text("Transcribe", size=14, font_family="Inter-SemiBold",
                                                   color=ft.Colors.WHITE)
            transcribe_button.style.mouse_cursor = ft.MouseCursor.CLICK
            page.update()

    transcribe_button = ft.Button(
        content=ft.Container(
            content=ft.Text("Transcribe", size=14, font_family="Inter-SemiBold", color=ft.Colors.WHITE),
            alignment=ft.Alignment.CENTER,
        ),
        expand=True,
        style=ft.ButtonStyle(
            bgcolor=ACCENT_PRIMARY,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.Padding.symmetric(horizontal=16, vertical=14),
            mouse_cursor=ft.MouseCursor.CLICK
        ),
        disabled=True,
        on_click=run_transcription
    )

    sidebar_content = ft.Container(
        content=ft.Column([
            ft.Container(height=15) if sys.platform.startswith("darwin") else ft.Container(height=5),
            ft.Row([
                ft.Container(
                    content=ft.Image(src=svg_logo),
                    width=48, height=48,
                    alignment=ft.Alignment.CENTER
                ),
                ft.Text("Whiscribe", size=22, font_family="Inter-SemiBold", color=TEXT_PRIMARY)
            ], alignment=ft.MainAxisAlignment.START, spacing=7),
            ft.Container(height=20),
            ft.Text("CONFIGURATION", size=11, font_family="Inter-SemiBold", color=TEXT_SECONDARY),
            ft.Container(height=10),
            ft.Row([model_dropdown]),
            ft.Container(height=5),
            ft.Row([language_dropdown]),
            ft.Container(expand=True),
            ft.Column([
                ft.Text(f"Whiscribe v{version}", size=11, color=TEXT_SECONDARY, text_align=ft.TextAlign.CENTER),
                ft.Text(f"Copyright © {datetime.now().year} silentsoft.org.", size=10, color=TEXT_SECONDARY,
                        text_align=ft.TextAlign.CENTER),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.CODE_ROUNDED,
                        icon_size=18,
                        icon_color=TEXT_SECONDARY,
                        tooltip="Source Code",
                        url="https://github.com/silentsoft/whiscribe",
                    ),
                    ft.IconButton(
                        icon=ft.Icons.FAVORITE_ROUNDED,
                        icon_size=18,
                        icon_color=ft.Colors.RED_400,
                        tooltip="Donate",
                        url="https://github.com/sponsors/silentsoft",
                    )
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
        ]),
        padding=ft.Padding.all(20),
        width=220,
        bgcolor=SURFACE_COLOR,
        border=ft.Border.only(right=ft.border.BorderSide(1, BORDER_COLOR)),
    )

    post_selection_area = ft.Container(
        content=ft.Column([
            ft.Container(height=10),
            ft.Row([track_dropdown]),
            hints_input,
            ft.Container(height=10),
            ft.Row([transcribe_button]),
            ft.Row([save_button]),
            ft.Container(height=10),
            srt_editor
        ], expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        visible=False,
        expand=True
    )

    main_dashboard = ft.Container(
        content=ft.Column([
            dropzone_card,
            post_selection_area
        ], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        padding=30,
        expand=True,
    )

    page.add(
        ft.Row(
            controls=[
                sidebar_content,
                main_dashboard
            ],
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=0,
        )
    )

    count_launch()


def prepare_environment():
    """Prepare the runtime environment for cross-platform execution."""
    def patch_window():
        # Essential for packaged apps (.exe, .app)
        multiprocessing.freeze_support()

        if sys.platform.startswith("win"):
            # Prevent CMD window from popping up
            _original_popen = subprocess.Popen
            def _patched_popen(*args, **kwargs):
                if "startupinfo" not in kwargs:
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    kwargs["startupinfo"] = si
                if "creationflags" not in kwargs:
                    kwargs["creationflags"] = 0x08000000 # CREATE_NO_WINDOW
                return _original_popen(*args, **kwargs)
            subprocess.Popen = _patched_popen
        else:
            try:
                # Prevent duplicate Flet window
                multiprocessing.set_start_method('fork', force=True)
            except RuntimeError:
                pass

    def patch_environ():
        path_list = os.environ.get("PATH", "").split(os.pathsep)
        updated = False

        # Add bundled bin directory to PATH
        base_dir = os.path.dirname(os.path.abspath(__file__))
        bundled_bin = os.path.join(base_dir, "bin")
        if os.path.exists(bundled_bin):
            # Ensure execution permissions (+x) for ffmpeg and ffprobe on macOS/Linux
            if not sys.platform.startswith("win"):
                for tool in ["ffmpeg", "ffprobe"]:
                    tool_path = os.path.join(bundled_bin, tool)
                    if os.path.exists(tool_path):
                        st = os.stat(tool_path)
                        # Check if user execute bit is missing
                        if not (st.st_mode & stat.S_IXUSR):
                            os.chmod(tool_path, st.st_mode | stat.S_IXUSR)

            if bundled_bin not in path_list:
                path_list.insert(0, bundled_bin)
                updated = True

        if updated:
            os.environ["PATH"] = os.pathsep.join(path_list)

    patch_window()
    patch_environ()


if __name__ == "__main__":
    prepare_environment()
    ft.run(main)
