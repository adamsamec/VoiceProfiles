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

		self.preventVoiceProfilesUpdate = False
		self.hasProfileSwitchedPreviously = False
		self.preventSetSynthIfSynthNotChanged = False
		self.voiceProfilesToRevert = None
		self.currentProfileName = consts.NORMAL_PROFILE_NAME
		self.synthsWithVoices = []

		self.loadSettingsFromConfig()
		self.addDefaultVoiceProfile()
		self.monkeyPatch()

	@property
	def currentVoiceProfilesIndex(self):
		return self.configProfilesIndices[self.currentProfileName]

	@currentVoiceProfilesIndex.setter
	def currentVoiceProfilesIndex(self, value):
		self.configProfilesIndices[self.currentProfileName] = value


	def monkeyPatch(self):
		synthDriverHandler.changeVoice = self.mpChangeVoice(synthDriverHandler.changeVoice)
		for methodName in ["first", "last", "increase", "increaseLarge", "decrease", "decreaseLarge"]:
			setattr(SynthSetting, methodName, self.mpRingChangeValue(getattr(SynthSetting, methodName)))

	def resetVoiceProfilesToRevert(self):
		if not self.hasProfileSwitchedPreviously:
			self.voiceProfilesToRevert = None

	def mpChangeVoice(self, func):
		def orig(synth, voiceId):
			ret = func(synth, voiceId)

			# We don't want synth and voice in profile to be updated when getting synth instance or when setting new synth during voice profile switch
			if self.preventVoiceProfilesUpdate:
				return ret

			self.hasProfileSwitchedPreviously = False

			# After some delay, consider the synth and voice change not to be caused by profile switching
			timer = Timer(0.2, self.resetVoiceProfilesToRevert)
			timer.start()

			# Skip voice update if configured so
			if not self.otherSettings["enableVoiceUpdateWhenNVDAsettingsChange"]:
				return ret

			if self.voiceProfilesToRevert == None:
				currentVoiceProfiles = self.voiceProfiles[self.currentVoiceProfilesIndex]
				self.voiceProfilesToRevert = {
					"synthId": currentVoiceProfiles["synthId"],
					"voiceId": currentVoiceProfiles["voiceId"]
				}
			synthId = SilenceSynthDriver.name if synth == None else synth.name
			if synth == None:
				voiceId = SilenceSynthDriver.name
			self.updateVoiceProfileSynthAndVoice(synthId, voiceId)
			return ret
		return orig
	
	def mpRingChangeValue(self, method):
		def orig(origSelf):
			ret = method(origSelf)
			param = origSelf.setting.id
			value = int(origSelf.value)
			if not param in consts.SAVED_PARAMS:
				return ret
			self.updateVoiceProfileParam(param, value)
			return ret
		return orig

	def handleProfileSwitch(self):
		self.hasProfileSwitchedPreviously = True
		newProfileName = config.conf.profiles[-1].name
		if not newProfileName:
			newProfileName = consts.NORMAL_PROFILE_NAME

		# Reverting hack is necessarybecause NVDA is missing a pre profile switch extension point 
		if self.voiceProfilesToRevert != None:
			self.updateVoiceProfileSynthAndVoice(self.voiceProfilesToRevert["synthId"], self.voiceProfilesToRevert["voiceId"])
			
		if not (newProfileName in self.configProfilesIndices):
			self.configProfilesIndices[newProfileName] = self.currentVoiceProfilesIndex
		self.currentProfileName = newProfileName
		if self.voiceProfilesToRevert != None:
			self.voiceProfilesToRevert = None

		# Ignore the synth and voice settings saved in the configuration profile and switch to the Voice Profile synth and voice instead
		self.preventSetSynthIfSynthNotChanged = True
		self.changeVoiceOnly(self.currentVoiceProfilesIndex, announceChange=False)
		self.preventSetSynthIfSynthNotChanged = False

	def cleanUpVoiceProfiles(self):
		self.updateSynthsWithVoices()
		self.currentVoiceProfilesIndex = self.deleteInvalidVoiceProfiles(startIndex=self.currentVoiceProfilesIndex)
		self.addDefaultVoiceProfile()

		# Fix for broken speech settings ring after deleting voices for some synths (e.g., Microsoft OneCore)
		synth = getSynth()
		if synth != None:
			setSynth(synth.name)

	def deleteInvalidVoiceProfiles(self, startIndex=0, dontChangeVoice=False):
		newValidIndex = startIndex
		doChangeVoice = False

		# Start deleting from start index
		index = self.findNextInvalid(startIndex)

		voiceProfilesLength = len(self.voiceProfiles)
		while voiceProfilesLength > 0 and index >= 0:
			del self.voiceProfiles[index]
			voiceProfilesLength = len(self.voiceProfiles)

			# If some voice profile before the current one has been deleted, shift the current index to the previous index and change the voice
			if index < self.currentVoiceProfilesIndex:
				self.currentVoiceProfilesIndex -= 1
				doChangeVoice = True

			# If the voice profile at the same index as the current profile voice has been deleted, change the voice
			elif index == self.currentVoiceProfilesIndex:
				doChangeVoice = True
				
			# If some voice profile before the start index has been deleted, shift the new valid index to the previous index
			if index < startIndex:
				newValidIndex -= 1

			index = self.findNextInvalid(index)

		# Check if list has been deleted entirely or was originally empty
		if voiceProfilesLength == 0:
			self.currentVoiceProfilesIndex = -1
			return -1
		
		if doChangeVoice and not dontChangeVoice:
			self.changeVoiceOnly(self.currentVoiceProfilesIndex, announceChange=False)

		# If we deleted the voice profile at the start index and after it, move index to 0
		if newValidIndex >= voiceProfilesLength:
			newValidIndex = 0
		return newValidIndex

	def findNextInvalid(self, startIndex):
		if len(self.voiceProfiles) == 0:
			return -1

		# If start index is out of list bounds, start at zero
		if startIndex < 0 or startIndex >= len(self.voiceProfiles):
			startIndex = 0

		index = startIndex
		while index >= 0 and self.synthAndVoiceExist(self.voiceProfiles[index]):
			# If list is empty, return not found
			if len(self.voiceProfiles) == 0:
				return -1
			index = self.getNextVoiceProfilesIndex(index)

			# If we are back on start, we have traversed entire list, so return not found
			if index == startIndex:
				return -1
		return index

	def synthAndVoiceExist(self, voiceProfile):
		synthExists = False
		voiceExists = False
		for synthWithVoices in self.synthsWithVoices:
			synthId = voiceProfile["synthId"]
			if synthWithVoices["id"] == synthId:
				synthExists = True
				if synthId == SilenceSynthDriver.name:
					voiceExists = True
					break
				voices = self.getVoicesForSynth(synthId)
				if voices == None:
					return False
				for voice in voices:
					if voice["id"] == voiceProfile["voiceId"]:
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
		self.addMissingProfileNames()

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
							self.preventVoiceProfilesUpdate = True
							instance = getSynthInstance(synthId)
							self.preventVoiceProfilesUpdate = False
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
		self.voiceProfiles = [json.loads(voiceProfile) for voiceProfile in self.getConfig("voiceProfiles")]
		self.configProfilesIndices = json.loads(self.getConfig("configProfilesIndices"))
		self.otherSettings = {
			"enableVoiceUpdateWhenNVDAsettingsChange": self.getConfig("enableVoiceUpdateWhenNVDAsettingsChange")
		}
		
		# Create index for naormal profile if not exists
		voiceProfilesLength = len(self.voiceProfiles)
		if not (consts.NORMAL_PROFILE_NAME in self.configProfilesIndices):
			if voiceProfilesLength > 0:
				self.configProfilesIndices[consts.NORMAL_PROFILE_NAME] = 0
			else:
				self.configProfilesIndices[consts.NORMAL_PROFILE_NAME] = -1

		if voiceProfilesLength == 0:
			# Set negative index for all configuration profiles if there are no voice profiles
			for profileName in self.configProfilesIndices:
				self.configProfilesIndices[profileName] = -1
		else:
			# Set index to 0 if index is out of voice profiles bounds for each configuration profile
			for profileName in self.configProfilesIndices:
				if self.configProfilesIndices[profileName] < 0 or self.configProfilesIndices[profileName] >= len(self.voiceProfiles):
					self.configProfilesIndices[profileName] = 0

	def saveSettingsTOConfig(self):
		voiceProfilesJson = [json.dumps(voiceProfile) for voiceProfile in self.voiceProfiles]
		self.setConfig("voiceProfiles", voiceProfilesJson)
		self.setConfig("configProfilesIndices", json.dumps(self.configProfilesIndices))
		self.setConfig("enableVoiceUpdateWhenNVDAsettingsChange", self.otherSettings["enableVoiceUpdateWhenNVDAsettingsChange"])

	def addDefaultVoiceProfile(self):
		# Create and add the default voice profile if does not exist
		if len(self.voiceProfiles) == 0:
			self.currentVoiceProfilesIndex = 0
			voiceProfile = self.getFreshVoiceProfile()
			if voiceProfile != None:
				self.voiceProfiles.append(voiceProfile)

	def addMissingProfileNames(self):
		for voiceProfile in self.voiceProfiles:
			if not "name" in voiceProfile:
				print("tester")
				print(voiceProfile["synthId"])
				print(voiceProfile["voiceId"])
				voiceProfile["name"] = self.getDefaultProfileName(voiceProfile["synthId"], voiceProfile["voiceId"])

	def getVoiceProfiles(self):
		return self.voiceProfiles.copy()

	def getOtherSettings(self):
		return self.otherSettings.copy()

	def getDefaultProfileName(self, synthId, voiceId):
		synthName = self.getSynthNameById(synthId)
		voiceName = self.getVoiceNameById(synthId, voiceId)
		print("testing")
		print(synthName)
		print(voiceName)
		if synthName == None or voiceName == None:
			# Translators: Default profile name for unknown voice
			profileName = _("Unknown")
		else:
			profileName = synthName if synthId == SilenceSynthDriver.name else f"{voiceName} ({synthName})"
		return profileName

	def applyVoiceProfiles(self, voiceProfiles):
		self.voiceProfiles = voiceProfiles.copy()
		self.changeVoiceOnly(self.currentVoiceProfilesIndex, announceChange=False)

	def applyOtherSettingsAndSave(self, otherSettings):
		self.otherSettings = otherSettings.copy()
		self.saveSettingsTOConfig()

	def switchToNextVoiceProfile(self):
		if len(self.voiceProfiles) == 0:
			return
		nextIndex = self.getNextVoiceProfilesIndex(self.currentVoiceProfilesIndex)
		self.changeVoice(nextIndex)

	def switchToPrevVoiceProfile(self):
		if len(self.voiceProfiles) == 0:
			return
		prevIndex = self.getPrevVoiceProfilesIndex(self.currentVoiceProfilesIndex)
		self.changeVoice(prevIndex)

	def showSelectVoiceProfileDialog(self):
		self.cleanUpVoiceProfiles()
		gui.mainFrame.prePopup()
		selectVoiceProfileDialog = SelectVoiceProfileDialog(gui.mainFrame, self)
		selectVoiceProfileDialog.Show()
		gui.mainFrame.postPopup()

	def getNextVoiceProfilesIndex(self, index):
		verifyResult = self.verifyIndex(index)
		if verifyResult <= 0:
			return verifyResult
		newIndex = (index + 1) % len(self.voiceProfiles)
		return newIndex

	def getPrevVoiceProfilesIndex(self, index):
		verifyResult = self.verifyIndex(index)
		if verifyResult <= 0:
			return verifyResult
		newIndex = (index - 1) % len(self.voiceProfiles)
		return newIndex

	def verifyIndex(self, index):
		voiceProfilesLength = len(self.voiceProfiles)
		if voiceProfilesLength == 0:
			return -1

		# If index is out of list bounds and list is not empty, return zero
		if index < 0 or index >= voiceProfilesLength:
			return 0

		return 1

	def changeVoice(self, newIndex, announceChange=True):
		newIndex = self.changeVoiceOnly(newIndex, announceChange)
		self.currentVoiceProfilesIndex = newIndex

	def changeVoiceOnly(self, newIndex, announceChange=True):
		voiceProfilesLength = len(self.voiceProfiles)
		if (newIndex >= voiceProfilesLength) or (newIndex < 0):
			if voiceProfilesLength > 0:
				return 0
			else:
				return -1
		
		# Determine the next voice profile
		newVoiceProfile = self.voiceProfiles[newIndex]

		# Delete all invalid voice profiles starting from the new index, and update the new index if necessary
		self.updateSynthsWithVoices()
		newIndex = self.deleteInvalidVoiceProfiles(startIndex=newIndex, dontChangeVoice=True)
		self.addDefaultVoiceProfile()
		voiceProfilesLength = len(self.voiceProfiles)
		if voiceProfilesLength == 0:
			# If after deleting all invalid voice profiles there were no voice profiles and we did not add a default one, return -1
			return -1
		elif newIndex == -1:
			# If after deleting all invalid voice profiles there were no voice profiles and we added a default one, set index to this default voice profile index
			newIndex = 0

		newVoiceProfile = self.voiceProfiles[newIndex]
		synth = getSynth()

		if newVoiceProfile["synthId"] == SilenceSynthDriver.name:
			if synth != None:
				setSynth(None)
		else:
			self.preventVoiceProfilesUpdate = True
			if not self.preventSetSynthIfSynthNotChanged or newVoiceProfile["synthId"] != synth.name:
				setSynth(newVoiceProfile["synthId"])
			self.preventVoiceProfilesUpdate = False
			synth = getSynth()
		
		# Apply new voice profile
		if newVoiceProfile["synthId"] != SilenceSynthDriver.name:
			synth.voice = newVoiceProfile["voiceId"]
			for param in consts.SAVED_PARAMS:
				if param in newVoiceProfile:
					setattr(synth, param, newVoiceProfile[param])
				else:
					setattr(synth, param, consts.DEFAULT_PARAMS_VALUES[param])
			if synth != None:
				synth.saveSettings()
		if announceChange and newVoiceProfile["synthId"] != SilenceSynthDriver.name:
			ui.message(newVoiceProfile["name"])
		return newIndex

	def updateVoiceProfileParam(self, param, value):
		if self.currentVoiceProfilesIndex < 0 or len(self.voiceProfiles) <= self.currentVoiceProfilesIndex:
			return None
		currentVoiceProfile = self.voiceProfiles[self.currentVoiceProfilesIndex]
		currentVoiceProfile[param] = value

	def updateVoiceProfileSynthAndVoice(self, synthId, voiceId):
		if self.currentVoiceProfilesIndex < 0 or len(self.voiceProfiles) <= self.currentVoiceProfilesIndex:
			return
		currentVoiceProfile = self.voiceProfiles[self.currentVoiceProfilesIndex]
		currentVoiceProfile["synthId"] = synthId
		currentVoiceProfile["voiceId"] = voiceId

	def getFreshVoiceProfile(self):
		synth = getSynth()
		if synth == None:
			synthId = SilenceSynthDriver.name
			voiceId = SilenceSynthDriver.name
		else:
			synthId = synth.name
			voiceId = synth.voice
		voiceProfile = {
			"synthId": synthId,
			"voiceId": voiceId,
		}
		for param in consts.SAVED_PARAMS:
			if hasattr(synth, param):
				voiceProfile[param] = getattr(synth, param)
		return voiceProfile

	def limitTextField(self, textField):
		value = textField.GetValue()
		insertionPoint = textField.GetInsertionPoint()
		if len(value) > consts.MAX_VOICE_PROFILE_NAME_LENGTH:
			textField.SetValue(value[:consts.MAX_VOICE_PROFILE_NAME_LENGTH])
			textField.SetInsertionPoint(insertionPoint)

	def getConfig(self, key):
		return config.conf["VoiceProfiles"][key]

	def setConfig(self, key, value):
		config.conf["VoiceProfiles"][key] = value

	def terminate(self):
		self.saveSettingsTOConfig()
