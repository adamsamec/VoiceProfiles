# Copyright 2025 Adam Samec <adam.samec@gmail.com>
# This add-on is free software, licensed under the terms of the GNU General Public License (version 2). see <https://www.gnu.org/licenses/gpl-2.0.html>.

import addonHandler
from synthDrivers.silence import SynthDriver as SilenceSynthDriver
import gui

import wx

addonHandler.initTranslation()

class SelectVoiceProfileDialog(wx.Dialog):
	_instance = None

	def __new__(cls, *args, **kwargs):
		if SelectVoiceProfileDialog._instance is None:
			return super(SelectVoiceProfileDialog, cls).__new__(cls, *args, **kwargs)
		return SelectVoiceProfileDialog._instance

	def __init__(self, parent, app):
		if SelectVoiceProfileDialog._instance is not None:
			return
		SelectVoiceProfileDialog._instance = self

		super(SelectVoiceProfileDialog, self).__init__(parent, title=_("Select a voice profile"))
		self.app = app
		self.voiceProfiles = self.app.getVoiceProfiles()
		self.doChangeVoice = False

		self.Bind(wx.EVT_CHAR_HOOK, self.charHook)
		self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroy)

		self.addWidgets()

	def addWidgets(self):
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		sHelper = gui.guiHelper.BoxSizerHelper(self, wx.VERTICAL)

		# Translators: Label for the voice profiles listbox in the Select a voice dialog
		self.voiceProfilesListBox = sHelper.addLabeledControl(_("Voice profiles"), wx.ListBox, choices=[])
		self.initVoiceProfilesListBox()

		# Buttons group
		buttons = gui.guiHelper.ButtonHelper(wx.VERTICAL)

		# Translators: Label for the OK button in the select a voice dialog
		self.okButton = buttons.addButton(self, label=_("OK"))
		self.okButton.Bind(wx.EVT_BUTTON, self.onOkButtonClick)
		self.okButton.SetDefault()

		# Translators: Label for the cancel button in the select voice dialog
		cancelButton = buttons.addButton(self, label=_("Cancel"))
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancelButtonClick)
		
		sHelper.addItem(buttons)
		mainSizer.Add(sHelper.sizer, border=10, flag=wx.ALL)
		mainSizer.Fit(self)
		self.SetSizer(mainSizer)

	def initVoiceProfilesListBox(self):
		listBoxItems = [voiceProfile["name"] for voiceProfile in self.voiceProfiles]
		self.voiceProfilesListBox.SetItems(listBoxItems)

	def charHook(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_ESCAPE:
			self.close()
		else:
			event.Skip()

	def onOkButtonClick(self, event):
		self.doChangeVoice = True
		self.close()

	def onCancelButtonClick(self, event):
		self.close()

	def close(self):
		self.Destroy()
		SelectVoiceProfileDialog._instance = None

	def onDestroy(self, event):
		if self.doChangeVoice:
			self.app.changeVoice(self.voiceProfilesListBox.GetSelection(), announceChange=False)
