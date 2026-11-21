# Voice Profiles

## Introduction

The Voice Profiles add-on for NVDA screen reader allows you to configure various voice profiles in its settings so that you can later quickly and easily switch between those profiles anytime either in forward or backward direction, or using the voice profile selection dialog.

This add-on comes handy for example in case you need to easily switch between voices in different languages, or between voices for ordinary work and long reading where you might want to configure two or more profiles with different voice or speech rate.

## Configuring voice profiles

The voice profiles to easily switch between can be preconfigured in the Voice Profiles add-on settings by following these steps:

1. Press NVDA + N to open the NVDA menu.
2. Choose the "Preferences" submenu.
3. Choose the "Settings" menu item.
4. Navigate to the "Voice Profiles" category. The Voice Profiles property page opens, and the voice profiles list will be populated only with the single voice profile for the current synthesizer and voice.
5. TO add another voice profile to the list, open the dialog for adding a new voice profile using the "Add" button.
6. Using the first combo box, Select the desired synthesizer first, then using the second combo box, select the synthesizer's desired voice which you want to set for the new voice profile.
7. Navigate to the "Profile name" edit field and type the desired name. By default, the edit field will be populated with the name determined by the selected synthesizer and voice from the previous step. The profile name you set here will be announced when switching to that profile.
8. Navigate to the "Add" button and activate it. The just added voice profile will appear in the voice profiles list after the currently selected item in the list.
9. Don't forgot to save the settings just made by pressing the "OK" or "Apply" button at the end of the NVDA settings dialog.

## Switching to next or previous voice profile using shortcuts

Let's say you speak English and French, then you can add two voice profiles in the Voice Profiles settings as described in the previous section, one using an English and the other using a French voice. Anytime later you can switch between those two voice profiles using only the NVDA + Control + L simple and comfortable keyboard shortcut instead of messing with the NVDA synth settings ring or the NVDA synthesizer selection dialog. If you configure mor than two voice profiles, you can also leverage the keyboard shortcut NVDA + Control + Shift + L for switching to the previous voice profile.

## Selecting voice profile using dialog

Especially in case you have configured mor than two voice profiles, you can take advantage of the voice profile selection dialog which can be invoked anytime using the NVDA + Alt + V keyboard shortcut. In the dialog, use the Down and Up arrow keys to select the desired voice profile from the list and switch to it using the Enter key.

## Other settings

You can control whether changes of the current voice using the synth settings ring, select synthesizer dialog, or via the speech category of the NVDA settings dialog also accordingly update the voice profiles configured in the Voice Profiles settings. This can be controlled in the Voice Profiles settings using the "Update voice when NVDA's own speech settings change" checkbox.

## Remembering voice profiles for individual applications

Let's say you want to browse the web in English, but want to make notes and all other work in French. Then you can have last used voice profile remembered in certain applications. For example, when you switch to Google Chrome, the voice profile automatically switches to the last used voice profile in that application, perhaps configured to use the English voice. Then when you go back to another application, for example to Microsoft Word to make notes in French, the voice profile automatically switches back to the default voice profile configured to use the French voice. This is enabled thanks to the NVDA configuration profiles feature.

TO configure certain application so that it remembers the last used voice profile, follow these steps:

1. Switch to that application, for example to Google Chrome.
2. Press NVDA + N to open the NVDA menu.
3. Choose the "Configuration profiles" menu item.
4. Press the "New" button.
5. Navigate to the radio button labelled as "Manual activation" under the "Use this profile for" grouping, and switch it to "Current application" using the Down arrow key.
6. Confirm the creation of a new configuration profile using the "OK" button.

## Changing Voice Profiles add-on shortcuts

The default NVDA + Control + L and NVDA + Control + Shift + L keyboard shortcuts for switching to the next or previous voice profile, respectively, as well as NVDA + Alt + V for showing the voice profiles selection dialog can be changed to another shortcuts using the "Input gestures" dialog as follows:

1. Press NVDA + N to open the NVDA menu.
2. Choose the "Preferences" submenu.
3. Choose the "Input gestures" menu item.
4. Type "voice" into the "Filter by" edit field.
5. In the tree, under the "Miscellaneous" category, navigate to the "Switches to the next voice profile", "Switches to the previous voice profile" or "Shows the dialog for selecting a voice profile" item depending on which shortcut you want to change.
6. Activate the "Add" button, then press the desired keyboard shortcut, and confirm with Enter.
7. Confirm the change using the "OK" button.

## Download

The Voice Profiles for NVDA add-on is available through NVDA Add-on Store, or can be [downloaded here][Voice Profiles download].

## Changelog

[The Voice Profiles changelog can be viewed here][changelog].

## Contact and feedback

If you have suggestions for the Voice Profiles add-on improvement, problems with its functionality, would like to provide a translation or have other comments, you can drop me an email to [adam.samec@gmail.com](mailto:adam.samec@gmail.com)

## License

The Voice Profiles add-on is available under the GNU General Public License version 2.0.

[Voice Profiles download]: https://files.adamsamec.cz/apps/nvda/VoiceProfiles.nvda-addon
[changelog]: https://github.com/adamsamec/VoiceProfiles/blob/main/Changelog.md
