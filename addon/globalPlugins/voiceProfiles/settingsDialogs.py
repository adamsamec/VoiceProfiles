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
		self.isVoiceProfilesModified = False

		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)

		# Translators: Label for the voice profiles listbox in the add-on settings
		self.voiceProfilesListBox = sHelper.addLabeledControl(_("Voice profiles"), wx.ListBox, choices=[])
		self.updateVoiceProfilesListBox()
		
		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the add button in the add-on settings
		self.addButton = buttons.addButton(self, label=_("Add"))
		self.addButton.Bind(wx.EVT_BUTTON, self.onAddButtonClick)

		# Translators: Label for the edit button in the add-on settings
		self.editButton = buttons.addButton(self, label=_("Edit"))
		self.editButton.Bind(wx.EVT_BUTTON, self.onEditButtonClick)

		# Translators: Label for the remove button in the add-on settings
		self.removeButton = buttons.addButton(self, label=_("Remove"))
		self.removeButton.Bind(wx.EVT_BUTTON, self.onRemoveButtonClick)
		self.updateRemoveButtonState()

		sHelper.addItem(buttons)

		# Translators: Label for the update voice when NVDA's own speech settings change checkbox in the add-on settings
		self.updateVoiceCheckbox = sHelper.addItem(wx.CheckBox(self, label=_("Update voice when NVDA's own speech settings change")))
		self.updateVoiceCheckbox.SetValue(self.otherSettings["enableVoiceUpdateWhenNVDAsettingsChange"])

	def loadSettings(self):
		self.app.cleanUpVoiceProfiles()
		self.voiceProfiles = self.app.getVoiceProfiles()
		self.otherSettings = self.app.getOtherSettings()

	def updateVoiceProfilesListBox(self, selectionIndex=0):
		listBoxItems = [voiceProfile["name"] for voiceProfile in self.voiceProfiles]
		self.voiceProfilesListBox.SetItems(listBoxItems)
		if len(listBoxItems) > 0:
			self.voiceProfilesListBox.SetSelection(selectionIndex)

	def addVoiceProfile(self, voiceProfile):
		insertIndex = 0 if len(self.voiceProfiles) == 0 else self.voiceProfilesListBox.GetSelection() + 1
		self.voiceProfiles.insert(insertIndex, voiceProfile)
		self.updateVoiceProfilesListBox(insertIndex)
		self.isVoiceProfilesModified = True
		self.updateRemoveButtonState()

	def saveVoiceProfile(self, voiceProfile, index):
		self.voiceProfiles[index] = voiceProfile
		self.updateVoiceProfilesListBox(index)
		self.isVoiceProfilesModified = True

	def onAddButtonClick(self, event):
		addVoiceProfileDialog = AddVoiceProfileDialog(self, self.app)
		addVoiceProfileDialog.ShowModal()

	def onEditButtonClick(self, event):
		editVoiceProfileDialog = EditVoiceProfileDialog(self, self.app)
		editVoiceProfileDialog.ShowModal()

	def onRemoveButtonClick(self, event):
		if len(self.voiceProfiles) == 1:
			ui.message(_("The last remaining voice profile cannot be removed"))
			return
		selectionIndex = self.voiceProfilesListBox.GetSelection()
		del self.voiceProfiles[selectionIndex]
		newSelectionIndex = max(0, min(selectionIndex, len(self.voiceProfiles) - 1))
		self.updateVoiceProfilesListBox(newSelectionIndex)
		self.isVoiceProfilesModified = True

	def updateRemoveButtonState(self):
		if len(self.voiceProfiles) > 0:
			self.removeButton.Enable()
		else:
			self.removeButton.Disable()

	def onSave(self):
		if self.isVoiceProfilesModified:
			self.app.applyVoiceProfiles(self.voiceProfiles)
			self.isVoiceProfilesModified = False

		self.otherSettings["enableVoiceUpdateWhenNVDAsettingsChange"] = self.updateVoiceCheckbox.GetValue()
		self.app.applyOtherSettingsAndSave(self.otherSettings)

class AddVoiceProfileDialog(wx.Dialog):

	def __init__(self, parent, app):
		super().__init__(parent, title=_("Add a voice profile"))
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
		# Translators: Label for the synthesizers combobox in the add voice profile dialog
		self.synthsComboBox = sHelper.addLabeledControl(_("Synthesizer"), wx.Choice, choices=synthsNames)
		self.synthsComboBox.Select(0)
		self.synthsComboBox.Bind(wx.EVT_CHOICE, self.onSynthChange)
		self.synthsComboBox.SetFocus()

		# Translators: Label for the voices combobox in the add voice profile dialog
		self.voicesComboBox = sHelper.addLabeledControl(_("Voice"), wx.Choice, choices=[])
		self.voicesComboBox.Bind(wx.EVT_CHOICE, self.onVoiceChange)

		# Translators: Label for the profile name text field in the add voice profile dialog
		self.profileNameTextField = sHelper.addLabeledControl(_("Profile name"), wx.TextCtrl)
		self.profileNameTextField.Bind(wx.EVT_TEXT, self.onProfileNameChange)

		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the add button in the add voice profile dialog
		self.addButton = buttons.addButton(self, label=_("Add"))
		self.addButton.Bind(wx.EVT_BUTTON, self.onAddButtonClick)
		self.addButton.SetDefault()

		# Translators: Label for the cancel button in the add voice profile dialog
		cancelButton = buttons.addButton(self, label=_("Cancel"))
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancelButtonClick)

		self.updateVoicesComboBox()
		self.setProfileNameTextBoxToDefault()

		sHelper.addItem(buttons)
		mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)

	def onSynthChange(self, event):
		self.updateVoicesComboBox()
		self.setProfileNameTextBoxToDefault()

	def onVoiceChange(self, event):
		self.setProfileNameTextBoxToDefault()

	def onProfileNameChange(self, event):
		self.app.limitTextField(self.profileNameTextField)

	def updateVoicesComboBox(self):
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

	def setProfileNameTextBoxToDefault(self):
		synthId = self.synthsIds[self.synthsComboBox.GetSelection()]
		voiceId = self.voicesIds[self.voicesComboBox.GetSelection()]
		profileName = self.app.getDefaultProfileName(synthId, voiceId)
		self.profileNameTextField.SetValue(profileName)

	def charHook(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_ESCAPE:
			self.close()
		else:
			event.Skip()

	def onAddButtonClick(self, event):
		voiceProfile = {
			"name": self.profileNameTextField.GetValue(),
			"synthId": self.synthsIds[self.synthsComboBox.GetSelection()],
			"voiceId": self.voicesIds[self.voicesComboBox.GetSelection()],
		}
		self.plugin.addVoiceProfile(voiceProfile)
		self.close()

	def onCancelButtonClick(self, event):
		self.close()

	def close(self):
		self.Destroy()


class EditVoiceProfileDialog(wx.Dialog):

	def __init__(self, parent, app):
		super().__init__(parent, title=_("Edit voice profile"))
		self.plugin = parent
		self.app = app
		self.voiceProfileIndex = self.plugin.voiceProfilesListBox.GetSelection()
		self.editedVoiceProfiles = self.plugin.voiceProfiles[self.voiceProfileIndex]

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
		# Translators: Label for the synthesizers combobox in the edit voice profile dialog
		self.synthsComboBox = sHelper.addLabeledControl(_("Synthesizer"), wx.Choice, choices=synthsNames)
		if self.editedVoiceProfiles["synthId"] in self.synthsIds:
			selection = self.synthsIds.index(self.editedVoiceProfiles["synthId"])
		else:
			selection = 0
		self.synthsComboBox.Select(selection)
		self.synthsComboBox.Bind(wx.EVT_CHOICE, self.onSynthChange)
		self.synthsComboBox.SetFocus()

		# Translators: Label for the voices combobox in the edit voice profile dialog
		self.voicesComboBox = sHelper.addLabeledControl(_("Voice"), wx.Choice, choices=[])
		self.voicesComboBox.Bind(wx.EVT_CHOICE, self.onVoiceChange)

		# Translators: Label for the profile name text field in the edit voice profile dialog
		self.profileNameTextField = sHelper.addLabeledControl(_("Profile name"), wx.TextCtrl)
		self.profileNameTextField.SetValue(self.editedVoiceProfiles["name"])
		self.profileNameTextField.Bind(wx.EVT_TEXT, self.onProfileNameChange)

		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the save button in the edit voice profile dialog
		self.saveButton = buttons.addButton(self, label=_("Save"))
		self.saveButton.Bind(wx.EVT_BUTTON, self.onSaveButtonClick)
		self.saveButton.SetDefault()

		# Translators: Label for the cancel button in the edit voice profile dialog
		cancelButton = buttons.addButton(self, label=_("Cancel"))
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancelButtonClick)

		self.updateVoicesComboBox()
		if self.editedVoiceProfiles["voiceId"] in self.voicesIds:
			selection = self.voicesIds.index(self.editedVoiceProfiles["voiceId"])
		else:
			selection = 0
		self.voicesComboBox.Select(selection)

		sHelper.addItem(buttons)
		mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)

	def onSynthChange(self, event):
		self.updateVoicesComboBox()
		self.setProfileNameTextBoxToDefault()

	def onVoiceChange(self, event):
		self.setProfileNameTextBoxToDefault()

	def onProfileNameChange(self, event):
		self.app.limitTextField(self.profileNameTextField)

	def updateVoicesComboBox(self):
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

				# Translators: Value of the voices combobox in the edit voice dialog when no voices are available
				comboBoxItems.append(_("No voices available"))
				self.saveButton.Disable()
			else:
				for voice in voices:
					self.voicesIds.append(voice["id"])
					comboBoxItems.append(voice["name"])
				self.saveButton.Enable()
		self.voicesComboBox.SetItems(comboBoxItems)
		self.voicesComboBox.Select(0)

	def charHook(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_ESCAPE:
			self.close()
		else:
			event.Skip()

	def onSaveButtonClick(self, event):
		voiceProfile = {
			"name": self.profileNameTextField.GetValue(),
			"synthId": self.synthsIds[self.synthsComboBox.GetSelection()],
			"voiceId": self.voicesIds[self.voicesComboBox.GetSelection()],
		}
		self.plugin.saveVoiceProfile(voiceProfile, self.voiceProfileIndex)
		self.close()

	def onCancelButtonClick(self, event):
		self.close()

	def close(self):
		self.Destroy()
