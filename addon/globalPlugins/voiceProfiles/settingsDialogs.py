# Copyright 2025 Adam Samec <adam.samec@gmail.com>
# This add-on is free software, licensed under the terms of the GNU General Public License (version 2). see <https://www.gnu.org/licenses/gpl-2.0.html>.

import addonHandler
from synthDrivers.silence import SynthDriver as SilenceSynthDriver
import ui
import gui
from gui.settingsDialogs import SettingsPanel

import weakref
import wx

import globalPlugins.voiceProfiles.consts as consts

addonHandler.initTranslation()

class OptionsPanel(SettingsPanel):
	_app = None

	# Translators: Add-on settings panel title
	title = _("Voice Profiles")

	def __init__ (self, *args, **kwargs):
		self.app = self._app()
		SettingsPanel.__init__(self, *args, **kwargs)

		self.Bind(wx.EVT_WINDOW_DESTROY, self.Cleanup)

	def Cleanup (self, event=None):
		if hasattr(self, "app"):
			del self.app
		if event != None:
			event.Skip()

	def __del__ (self):
		self.Cleanup()

	@classmethod
	def setAppInstance (cls, instance):
		cls._app = weakref.ref(instance)

	def makeSettings(self, settingsSizer):
		self.loadSettings()
		self.isVoiceProfileSettingsModified = False

		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: Label for the voice profiles listbox in the add-on settings
		self.voiceProfilesListBox = sHelper.addLabeledControl(_("Voice profiles"), wx.ListBox, choices=[])
		self.updateVoiceProfilesListBox()
		
		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the add button in the add-on settings
		self.addButton = buttons.addButton(self, label=_("Add"))
		self.addButton.Bind(wx.EVT_BUTTON, self.onAddButtonClick)

		# Translators: Label for the remove button in the add-on settings
		self.removeButton = buttons.addButton(self, label=_("Remove"))
		self.removeButton.Bind(wx.EVT_BUTTON, self.onRemoveButtonClick)
		self.updateRemoveButtonState()

		sHelper.addItem(buttons)

		# Translators: Label for the update voice profile parameters when NVDA's own speech settings change checkbox in the add-on settings
		self.updateVoiceProfileParametersCheckbox = sHelper.addItem(wx.CheckBox(self, label=_("Update voice profile parameters when NVDA's own speech settings change")))
		self.updateVoiceProfileParametersCheckbox.SetValue(self.otherSettings["enableVoiceProfileUpdateWhenNVDAsettingsChange"])

	def loadSettings(self):
		self.app.cleanUpVoiceProfileSettings()
		self.voiceProfileSettings = self.app.getVoiceProfileSettings()
		self.otherSettings = self.app.getOtherSettings()

	def updateVoiceProfilesListBox(self, selectionIndex=0):
		listBoxItems = []
		for voiceProfileSetting in self.voiceProfileSettings:
			synthName = self.app.getSynthNameById(voiceProfileSetting["synthId"])
			voiceName = self.app.getVoiceNameById(voiceProfileSetting["synthId"], voiceProfileSetting["voiceId"])
			choice = synthName if voiceProfileSetting["synthId"] == SilenceSynthDriver.name else f"{voiceName} ({synthName})"
			listBoxItems.append(choice)
		self.voiceProfilesListBox.SetItems(listBoxItems)
		if len(listBoxItems) > 0:
			self.voiceProfilesListBox.SetSelection(selectionIndex)

	def addVoiceProfileSetting(self, setting):
		insertIndex = 0 if len(self.voiceProfileSettings) == 0 else self.voiceProfilesListBox.GetSelection() + 1
		self.voiceProfileSettings.insert(insertIndex, setting)
		self.updateVoiceProfilesListBox(insertIndex)
		self.updateRemoveButtonState()
		self.isVoiceProfileSettingsModified = True

	def onAddButtonClick(self, event):
		addVoiceProfileDialog = AddVoiceProfileDialog(self, self.app)
		addVoiceProfileDialog.ShowModal()

	def onRemoveButtonClick(self, event):
		if len(self.voiceProfileSettings) == 1:
			ui.message(_("The last remaining voice profile cannot be removed"))
			return
		selectionIndex = self.voiceProfilesListBox.GetSelection()
		del self.voiceProfileSettings[selectionIndex]
		newSelectionIndex = max(0, min(selectionIndex, len(self.voiceProfileSettings) - 1))
		self.updateVoiceProfilesListBox(newSelectionIndex)
		self.isVoiceProfileSettingsModified = True

	def updateRemoveButtonState(self):
		if len(self.voiceProfileSettings) > 0:
			self.removeButton.Enable()
		else:
			self.removeButton.Disable()

	def onSave(self):
		if self.isVoiceProfileSettingsModified:
			self.app.applyVoiceProfileSettings(self.voiceProfileSettings)
			self.isVoiceProfileSettingsModified = False

		self.otherSettings["enableVoiceProfileUpdateWhenNVDAsettingsChange"] = self.updateVoiceProfileParametersCheckbox.GetValue()
		self.app.applyOtherSettingsAndSave(self.otherSettings)

class AddVoiceProfileDialog(wx.Dialog):

	def __init__(self, parent, app):
		super().__init__(parent, title=_("Add voice profile"))
		self.plugin = parent
		self.app = app

		self.Bind(wx.EVT_CHAR_HOOK, self.charHook)
		self.addWidgets()

	def addWidgets(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Synth combobox
		self.app.updateSynthsWithVoices()
		synthsWithVoices = self.app.getSynthsWithVoices()
		self.synthsIds = [synthWithVoices["id"] for synthWithVoices in synthsWithVoices]
		synthsNames = [synthWithVoices["name"] for synthWithVoices in synthsWithVoices]
		# Translators: Label for the synthesizers combobox in the add voice dialog
		self.synthsComboBox = sHelper.addLabeledControl(_("Synthesizer"), wx.Choice, choices=synthsNames)
		self.synthsComboBox.Select(0)
		self.synthsComboBox.Bind(wx.EVT_CHOICE, self.onSynthChange)
		self.synthsComboBox.SetFocus()

		# Translators: Label for the voices combobox in the add voice dialog
		self.voicesComboBox = sHelper.addLabeledControl(_("Voice"), wx.Choice, choices=[])

		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the add button in the add voice dialog
		self.addButton = buttons.addButton(self, label=_("Add"))
		self.addButton.Bind(wx.EVT_BUTTON, self.onAddButtonClick)
		self.addButton.SetDefault()

		# Translators: Label for the cancel button in the add voice dialog
		cancelButton = buttons.addButton(self, label=_("Cancel"))
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancelButtonClick)
		
		self.updateVoiceComboBox()
		
		sHelper.addItem(buttons)
		mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)

	def onSynthChange(self, event):
		self.updateVoiceComboBox()

	def updateVoiceComboBox(self):
		comboBoxItems = []
		synthSelection = self.synthsComboBox.GetSelection()
		synthId = self.synthsIds[synthSelection]		
		self.voicesIds = []
		if synthId == SilenceSynthDriver.name:
		# Special treatment for silence synth
			self.voicesIds = [SilenceSynthDriver.name]
			comboBoxItems = [consts.SILENCE_VOICE_NAME]
		else:
			voices = self.app.getVoicesForSynth(synthId)
			if voices == None:

				# Translators: Value of the voices combobox in the add voice dialog when no voices are available
				comboBoxItems.append(_("No voices available"))
				self.addButton.Disable()
			else:
				for voice in voices:
					self.voicesIds.append(voice["id"])
					comboBoxItems.append(voice["name"])
				self.addButton.Enable()
		self.voicesComboBox.SetItems(comboBoxItems)
		self.voicesComboBox.Select(0)

	def charHook(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_ESCAPE:
			self.close()
		else:
			event.Skip()

	def onAddButtonClick(self, event):
		voiceProfileSetting = {
			"synthId": self.synthsIds[self.synthsComboBox.GetSelection()],
			"voiceId": self.voicesIds[self.voicesComboBox.GetSelection()],
		}
		self.plugin.addVoiceProfileSetting(voiceProfileSetting)
		self.close()

	def onCancelButtonClick(self, event):
		self.close()

	def close(self):
		self.Destroy()
