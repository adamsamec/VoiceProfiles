# Copyright 2025 Adam Samec <adam.samec@gmail.com>
# This add-on is free software, licensed under the terms of the GNU General Public License (version 2). see <https://www.gnu.org/licenses/gpl-2.0.html>.

from synthSettingsRing import SynthSetting
import addonHandler
import synthDriverHandler
from synthDriverHandler import getSynth, setSynth, getSynthList, getSynthInstance
from synthDrivers.silence import SynthDriver as SilenceSynthDriver
import config
import ui
import gui

import json
from threading import Timer
import wx

import globalPlugins.voiceProfiles.consts as consts
from .settingsDialogs import OptionsPanel
from .selectVoiceProfileDialog import SelectVoiceProfileDialog

addonHandler.initTranslation()

class VoiceProfiles:

	def __init__(self):
		OptionsPanel.setAppInstance(self)
		config.conf.spec["VoiceProfiles"] = consts.CONFIG_SPEC

		self.preventVoiceProfileSettingsUpdate = False
		self.hasProfileSwitchedPreviously = False
		self.voiceProfileSettingsToRevert = None
		self.currentProfileName = consts.NORMAL_PROFILE_NAME
		self.synthsWithVoices = []

		self.loadSettingsFromConfig()
		self.addDefaultVoiceProfileSetting()
		self.monkeyPatch()

	@property
	def currentVoiceProfileSettingsIndex(self):
		return self.profilesVoiceProfileSettingsIndices[self.currentProfileName]

	@currentVoiceProfileSettingsIndex.setter
	def currentVoiceProfileSettingsIndex(self, value):
		self.profilesVoiceProfileSettingsIndices[self.currentProfileName] = value


	def monkeyPatch(self):
		synthDriverHandler.changeVoice = self.mpChangeVoice(synthDriverHandler.changeVoice)
		for methodName in ["first", "last", "increase", "increaseLarge", "decrease", "decreaseLarge"]:
			setattr(SynthSetting, methodName, self.mpRingChangeValue(getattr(SynthSetting, methodName)))

	def resetVoiceProfileSettingsToRevert(self):
		if not self.hasProfileSwitchedPreviously:
			self.voiceProfileSettingsToRevert = None

	def mpChangeVoice(self, func):
		def orig(synth, voiceId):
			ret = func(synth, voiceId)

			# We don't want synth and voice settings to be updated when getting synth instance or when setting new synth during voice profile switch
			if self.preventVoiceProfileSettingsUpdate:
				return ret

			self.hasProfileSwitchedPreviously = False

			# After some delay, consider the synth and voice change not to be caused by profile switching
			timer = Timer(0.2, self.resetVoiceProfileSettingsToRevert)
			timer.start()

			# Skip voice update if configured so
			if not self.otherSettings["enableVoiceProfileUpdateWhenNVDAsettingsChange"]:
				return ret

			if self.voiceProfileSettingsToRevert == None:
				currentVoiceProfileSettings = self.voiceProfileSettings[self.currentVoiceProfileSettingsIndex]
				self.voiceProfileSettingsToRevert = {
					"synthId": currentVoiceProfileSettings["synthId"],
					"voiceId": currentVoiceProfileSettings["voiceId"]
				}
			synthId = SilenceSynthDriver.name if synth == None else synth.name
			if synth == None:
				voiceId = SilenceSynthDriver.name
			self.updateVoiceProfileSettingSynthAndVoice(synthId, voiceId)
			return ret
		return orig
	
	def mpRingChangeValue(self, method):
		def orig(origSelf):
			ret = method(origSelf)
			param = origSelf.setting.id
			value = int(origSelf.value)
			if not param in consts.SAVED_PARAMS:
				return ret
			self.updateVoiceProfileSettingParam(param, value)
			return ret
		return orig

	def handleProfileSwitch(self):
		self.hasProfileSwitchedPreviously = True
		newProfileName = config.conf.profiles[-1].name
		if not newProfileName:
			newProfileName = consts.NORMAL_PROFILE_NAME

		# Reverting hack is necessarybecause NVDA is missing a pre profile switch extension point 
		if self.voiceProfileSettingsToRevert != None:
			self.updateVoiceProfileSettingSynthAndVoice(self.voiceProfileSettingsToRevert["synthId"], self.voiceProfileSettingsToRevert["voiceId"])
			
		if not (newProfileName in self.profilesVoiceProfileSettingsIndices):
			self.profilesVoiceProfileSettingsIndices[newProfileName] = self.currentVoiceProfileSettingsIndex
		self.currentProfileName = newProfileName
		if self.voiceProfileSettingsToRevert != None:
			self.voiceProfileSettingsToRevert = None

		# Ignore the synth and voice settings saved in the profile and switch to the Voice Profiles settings instead
		self.changeVoiceOnly(self.currentVoiceProfileSettingsIndex, announceChange=False)

	def cleanUpVoiceProfileSettings(self):
		self.updateSynthsWithVoices()
		self.currentVoiceProfileSettingsIndex = self.deleteInvalidVoiceProfileSettings(startIndex=self.currentVoiceProfileSettingsIndex)
		self.addDefaultVoiceProfileSetting()

		# Fix for broken speech settings ring after deleting voices for some synths (e.g., Microsoft OneCore)
		synth = getSynth()
		if synth != None:
			setSynth(synth.name)

	def deleteInvalidVoiceProfileSettings(self, startIndex=0, dontChangeVoice=False):
		newValidIndex = startIndex
		doChangeVoice = False

		# Start deleting from start index
		index = self.findNextInvalid(startIndex)

		voiceProfileSettingsLength = len(self.voiceProfileSettings)
		while voiceProfileSettingsLength > 0 and index >= 0:
			del self.voiceProfileSettings[index]
			voiceProfileSettingsLength = len(self.voiceProfileSettings)

			# If some setting before the current one has been deleted, shift the current index to the previous index and change the voice
			if index < self.currentVoiceProfileSettingsIndex:
				self.currentVoiceProfileSettingsIndex -= 1
				doChangeVoice = True

			# If setting at the same index as the current setting has been deleted, change the voice
			elif index == self.currentVoiceProfileSettingsIndex:
				doChangeVoice = True
				
			# If some setting before the start index has been deleted, shift the new valid index to the previous index
			if index < startIndex:
				newValidIndex -= 1

			index = self.findNextInvalid(index)

		# Check if list has been deleted entirely or was originally empty
		if voiceProfileSettingsLength == 0:
			self.currentVoiceProfileSettingsIndex = -1
			return -1
		
		if doChangeVoice and not dontChangeVoice:
			self.changeVoiceOnly(self.currentVoiceProfileSettingsIndex, announceChange=False)

		# If we deleted voice settings at the start index and after it, move index to 0
		if newValidIndex >= voiceProfileSettingsLength:
			newValidIndex = 0
		return newValidIndex

	def findNextInvalid(self, startIndex):
		if len(self.voiceProfileSettings) == 0:
			return -1

		# If start index is out of list bounds, start at zero
		if startIndex < 0 or startIndex >= len(self.voiceProfileSettings):
			startIndex = 0

		index = startIndex
		while index >= 0 and self.synthAndVoiceExist(self.voiceProfileSettings[index]):
			# If list is empty, return not found
			if len(self.voiceProfileSettings) == 0:
				return -1
			index = self.getNextVoiceProfileSettingsIndex(index)

			# If we are back on start, we have traversed entire list, so return not found
			if index == startIndex:
				return -1
		return index

	def synthAndVoiceExist(self, voiceProfileSetting):
		synthExists = False
		voiceExists = False
		for synthWithVoices in self.synthsWithVoices:
			synthId = voiceProfileSetting["synthId"]
			if synthWithVoices["id"] == synthId:
				synthExists = True
				if synthId == SilenceSynthDriver.name:
					voiceExists = True
					break
				voices = self.getVoicesForSynth(synthId)
				if voices == None:
					return False
				for voice in voices:
					if voice["id"] == voiceProfileSetting["voiceId"]:
						voiceExists = True
						break
				else:
					continue
				break # Executed only if inner loop broke
		return synthExists and voiceExists

	def updateSynthsWithVoices(self):
		newSynthsWithVoices = []
		synthsInfos = getSynthList()
		for synthInfo in synthsInfos:
			synthId = synthInfo[0]
			try:
				# Try finding existing synth with voices dict and appending it
				existingSynthWithVoices = next(synthWithVoices for synthWithVoices in self.synthsWithVoices if synthWithVoices["id"] == synthId)
				newSynthsWithVoices.append(existingSynthWithVoices)
			except StopIteration:
				# If not already exists, append the new synth with voices dict
				isSilence = synthId == SilenceSynthDriver.name
				synthName = consts.SILENCE_VOICE_NAME if isSilence else synthInfo[1]
				newSynthsWithVoices.append({
					"id": synthId,
					"name": synthName,
					"voices": None
				})
		self.synthsWithVoices = newSynthsWithVoices

	def getSynthsWithVoices(self):
		return self.synthsWithVoices.copy()

	def getVoicesForSynth(self, synthId):
		if synthId == SilenceSynthDriver.name:
			return None
		for synthWithVoices in self.synthsWithVoices:
			if synthWithVoices["id"] == synthId:
				if synthWithVoices["voices"] == None:
					synth = getSynth()
					if synth == None:
						return None
					if synth.name== synthId:
						voices = synth.availableVoices
						synthWithVoices["voices"] = [{"id": id, "name": voices[id].displayName} for id in voices]
					else:
						try:
							self.preventVoiceProfileSettingsUpdate = True
							instance = getSynthInstance(synthId)
							self.preventVoiceProfileSettingsUpdate = False
							voices = instance.availableVoices
							synthWithVoices["voices"] = [{"id": id, "name": voices[id].displayName} for id in voices]
							instance.terminate()
							del instance
						except:
							return None
				return synthWithVoices["voices"]
		return None

	def getSynthNameById(self, synthId):
		try:
			synthName = next(synthWithVoices["name"] for synthWithVoices in self.synthsWithVoices if synthWithVoices["id"] == synthId)
			return synthName
		except StopIteration:
			return None

	def getVoiceNameById(self, synthId, voiceId):
		voices = self.getVoicesForSynth(synthId)
		if voices == None:
			return None
		try:
			voiceName = next(voice["name"] for voice in voices if voice["id"] == voiceId)
			return voiceName
		except StopIteration:
			return None

	def loadSettingsFromConfig(self):
		self.voiceProfileSettings = [json.loads(voiceProfileSetting) for voiceProfileSetting in self.getConfig("voiceProfileSettings")]
		self.profilesVoiceProfileSettingsIndices = json.loads(self.getConfig("profilesVoiceProfileSettingsIndices"))
		self.otherSettings = {
			"enableVoiceProfileUpdateWhenNVDAsettingsChange": self.getConfig("enableVoiceProfileUpdateWhenNVDAsettingsChange")
		}
		
		# Create index for naormal profile if not exists
		voiceProfileSettingsLength = len(self.voiceProfileSettings)
		if not (consts.NORMAL_PROFILE_NAME in self.profilesVoiceProfileSettingsIndices):
			if voiceProfileSettingsLength > 0:
				self.profilesVoiceProfileSettingsIndices[consts.NORMAL_PROFILE_NAME] = 0
			else:
				self.profilesVoiceProfileSettingsIndices[consts.NORMAL_PROFILE_NAME] = -1

		if voiceProfileSettingsLength == 0:
			# Set negative index for all profiles if there are no voice settings
			for profileName in self.profilesVoiceProfileSettingsIndices:
				self.profilesVoiceProfileSettingsIndices[profileName] = -1
		else:
			# Set index to 0 if index is out of voice settings bounds for each profile
			for profileName in self.profilesVoiceProfileSettingsIndices:
				if self.profilesVoiceProfileSettingsIndices[profileName] < 0 or self.profilesVoiceProfileSettingsIndices[profileName] >= len(self.voiceProfileSettings):
					self.profilesVoiceProfileSettingsIndices[profileName] = 0

	def saveSettingsTOConfig(self):
		voiceProfileSettingsJson = [json.dumps(voiceProfileSetting) for voiceProfileSetting in self.voiceProfileSettings]
		self.setConfig("voiceProfileSettings", voiceProfileSettingsJson)
		self.setConfig("profilesVoiceProfileSettingsIndices", json.dumps(self.profilesVoiceProfileSettingsIndices))
		self.setConfig("enableVoiceProfileUpdateWhenNVDAsettingsChange", self.otherSettings["enableVoiceProfileUpdateWhenNVDAsettingsChange"])

	def addDefaultVoiceProfileSetting(self):
		# Create and add the default voice setting if does not exist
		if len(self.voiceProfileSettings) == 0:
			self.currentVoiceProfileSettingsIndex = 0
			voiceProfileSetting = self.getFreshVoiceProfileSetting()
			if voiceProfileSetting != None:
				self.voiceProfileSettings.append(voiceProfileSetting)

	def getVoiceProfileSettings(self):
		return self.voiceProfileSettings.copy()

	def getOtherSettings(self):
		return self.otherSettings.copy()

	def applyVoiceProfileSettings(self, voiceProfileSettings):
		self.voiceProfileSettings = voiceProfileSettings.copy()
		self.changeVoiceOnly(self.currentVoiceProfileSettingsIndex, announceChange=False)

	def applyOtherSettingsAndSave(self, otherSettings):
		self.otherSettings = otherSettings.copy()
		self.saveSettingsTOConfig()

	def switchToNextVoiceProfile(self):
		if len(self.voiceProfileSettings) == 0:
			return
		nextIndex = self.getNextVoiceProfileSettingsIndex(self.currentVoiceProfileSettingsIndex)
		self.changeVoice(nextIndex)

	def switchToPrevVoiceProfile(self):
		if len(self.voiceProfileSettings) == 0:
			return
		prevIndex = self.getPrevVoiceProfileSettingsIndex(self.currentVoiceProfileSettingsIndex)
		self.changeVoice(prevIndex)

	def showSelectVoiceProfileDialog(self):
		self.cleanUpVoiceProfileSettings()
		gui.mainFrame.prePopup()
		selectVoiceProfileDialog = SelectVoiceProfileDialog(gui.mainFrame, self)
		selectVoiceProfileDialog.Show()
		gui.mainFrame.postPopup()

	def getNextVoiceProfileSettingsIndex(self, index):
		verifyResult = self.verifyIndex(index)
		if verifyResult <= 0:
			return verifyResult
		newIndex = (index + 1) % len(self.voiceProfileSettings)
		return newIndex

	def getPrevVoiceProfileSettingsIndex(self, index):
		verifyResult = self.verifyIndex(index)
		if verifyResult <= 0:
			return verifyResult
		newIndex = (index - 1) % len(self.voiceProfileSettings)
		return newIndex

	def verifyIndex(self, index):
		voiceProfileSettingsLength = len(self.voiceProfileSettings)
		if voiceProfileSettingsLength == 0:
			return -1

		# If index is out of list bounds and list is not empty, return zero
		if index < 0 or index >= voiceProfileSettingsLength:
			return 0

		return 1

	def changeVoice(self, newIndex, announceChange=True):
		newIndex = self.changeVoiceOnly(newIndex, announceChange)
		self.currentVoiceProfileSettingsIndex = newIndex

	def changeVoiceOnly(self, newIndex, announceChange=True):
		voiceProfileSettingsLength = len(self.voiceProfileSettings)
		if (newIndex >= voiceProfileSettingsLength) or (newIndex < 0):
			if voiceProfileSettingsLength > 0:
				return 0
			else:
				return -1
		
		# Determine the next voice setting
		newVoiceProfileSetting = self.voiceProfileSettings[newIndex]

		# Delete all invalid voice settings starting from the new index, and update the new index if necessary
		self.updateSynthsWithVoices()
		newIndex = self.deleteInvalidVoiceProfileSettings(startIndex=newIndex, dontChangeVoice=True)
		self.addDefaultVoiceProfileSetting()
		voiceProfileSettingsLength = len(self.voiceProfileSettings)
		if voiceProfileSettingsLength == 0:
			# If after deleting all invalid voice settings there were no voice settings and we did not add a default one, return -1
			return -1
		elif newIndex == -1:
			# If after deleting all invalid voice settings there were no voice settings and we added a default one, set index to this default voice setting index
			newIndex = 0

		newVoiceProfileSetting = self.voiceProfileSettings[newIndex]
		synth = getSynth()

		if newVoiceProfileSetting["synthId"] == SilenceSynthDriver.name:
			if synth != None:
				setSynth(None)
		else:
			self.preventVoiceProfileSettingsUpdate = True
			setSynth(newVoiceProfileSetting["synthId"])
			self.preventVoiceProfileSettingsUpdate = False
			synth = getSynth()
		
		# Apply new voice setting
		if newVoiceProfileSetting["synthId"] != SilenceSynthDriver.name:
			synth.voice = newVoiceProfileSetting["voiceId"]
			for param in consts.SAVED_PARAMS:
				if param in newVoiceProfileSetting:
					setattr(synth, param, newVoiceProfileSetting[param])
				else:
					setattr(synth, param, consts.DEFAULT_PARAMS_VALUES[param])
			if synth != None:
				synth.saveSettings()
		if announceChange and newVoiceProfileSetting["synthId"] != SilenceSynthDriver.name:
			voiceName = self.getVoiceNameById(newVoiceProfileSetting["synthId"], newVoiceProfileSetting["voiceId"])
			ui.message(voiceName)
		return newIndex

	def updateVoiceProfileSettingParam(self, param, value):
		if self.currentVoiceProfileSettingsIndex < 0 or len(self.voiceProfileSettings) <= self.currentVoiceProfileSettingsIndex:
			return None
		currentVoiceProfileSetting = self.voiceProfileSettings[self.currentVoiceProfileSettingsIndex]
		currentVoiceProfileSetting[param] = value

	def updateVoiceProfileSettingSynthAndVoice(self, synthId, voiceId):
		if self.currentVoiceProfileSettingsIndex < 0 or len(self.voiceProfileSettings) <= self.currentVoiceProfileSettingsIndex:
			return
		currentVoiceProfileSetting = self.voiceProfileSettings[self.currentVoiceProfileSettingsIndex]
		currentVoiceProfileSetting["synthId"] = synthId
		currentVoiceProfileSetting["voiceId"] = voiceId

	def getFreshVoiceProfileSetting(self):
		synth = getSynth()
		if synth == None:
			synthId = SilenceSynthDriver.name
			voiceId = SilenceSynthDriver.name
		else:
			synthId = synth.name
			voiceId = synth.voice
		voiceProfileSetting = {
			"synthId": synthId,
			"voiceId": voiceId,
		}
		for param in consts.SAVED_PARAMS:
			if hasattr(synth, param):
				voiceProfileSetting[param] = getattr(synth, param)
		return voiceProfileSetting

	def getConfig(self, key):
		return config.conf["VoiceProfiles"][key]

	def setConfig(self, key, value):
		config.conf["VoiceProfiles"][key] = value

	def terminate(self):
		self.saveSettingsTOConfig()
