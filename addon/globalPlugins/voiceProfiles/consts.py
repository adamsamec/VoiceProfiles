# Copyright 2025 Adam Samec <adam.samec@gmail.com>
# This add-on is free software, licensed under the terms of the GNU General Public License (version 2). see <https://www.gnu.org/licenses/gpl-2.0.html>.

import addonHandler

addonHandler.initTranslation()

# Constants
# Translators: Label for the silence synthesizer in the voices listbox or synthesizers and voices comboboxes
SILENCE_VOICE_NAME = _("Silence")

NORMAL_PROFILE_NAME = "[normal]"
CONFIG_SPEC = {
	"voiceProfileSettings": "string_list(default=list())",
	"profilesVoiceProfileSettingsIndices": "string(default='{}')",
	"enableVoiceProfileUpdateWhenNVDAsettingsChange": "boolean(default=True)",
}
SAVED_PARAMS = ["volume", "rate", "rateBoost"]
DEFAULT_PARAMS_VALUES = {
	"volume": 100,
	"rate": 50,
	"rateBoost": 0
}
MAX_VOICE_PROFILE_NAME_LENGTH = 150
