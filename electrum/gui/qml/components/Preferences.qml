import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material

import org.electrum 1.0

import "controls"

Pane {
    id: preferences
    objectName: 'Properties'

    property string title: qsTr("Preferences")

    padding: 0

    property var _baseunits: ['FACT','mFACT','bits','sat']

    ColumnLayout {
        anchors.fill: parent

        Flickable {
            Layout.fillHeight: true
            Layout.fillWidth: true

            contentHeight: prefsPane.height
            interactive: height < contentHeight
            clip: true

            Pane {
                id: prefsPane
                width: parent.width

                GridLayout {
                    columns: 2
                    width: parent.width

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('User Interface')
                    }

                    Label {
                        text: qsTr('Language')
                    }

                    ElComboBox {
                        id: language
                        textRole: 'text'
                        valueRole: 'value'
                        model: Config.languagesAvailable
                        onCurrentValueChanged: {
                            if (activeFocus) {
                                if (Config.language != currentValue) {
                                    Config.language = currentValue
                                    var dialog = app.messageDialog.createObject(app, {
                                        text: qsTr('Please restart Electrum to activate the new GUI settings')
                                    })
                                    dialog.open()
                                }
                            }
                        }
                    }

                    Label {
                        text: qsTr('Base unit')
                    }

                    ElComboBox {
                        id: baseUnit
                        model: _baseunits
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Config.baseUnit = currentValue
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        spacing: 0
                        Switch {
                            id: thousands
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.thousandsSeparator = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Add thousands separators to Fact0rn amounts')
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        spacing: 0
                        Switch {
                            id: fiatEnable
                            onCheckedChanged: {
                                if (activeFocus)
                                    Daemon.fx.enabled = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Fiat Currency')
                            wrapMode: Text.Wrap
                        }
                    }

                    ElComboBox {
                        id: currencies
                        model: Daemon.fx.currencies
                        enabled: Daemon.fx.enabled
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Daemon.fx.fiatCurrency = currentValue
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        spacing: 0
                        Switch {
                            id: historicRates
                            enabled: Daemon.fx.enabled
                            onCheckedChanged: {
                                if (activeFocus)
                                    Daemon.fx.historicRates = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Historic rates')
                            wrapMode: Text.Wrap
                        }
                    }

                    Label {
                        text: qsTr('Exchange rate provider')
                        enabled: Daemon.fx.enabled
                    }

                    ElComboBox {
                        id: rateSources
                        enabled: Daemon.fx.enabled
                        model: Daemon.fx.rateSources
                        onModelChanged: {
                            currentIndex = rateSources.indexOfValue(Daemon.fx.rateSource)
                        }
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Daemon.fx.rateSource = currentValue
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 0
                        Switch {
                            id: usePin
                            checked: Config.pinCode
                            onCheckedChanged: {
                                if (activeFocus) {
                                    console.log('PIN active ' + checked)
                                    if (checked) {
                                        var dialog = pinSetup.createObject(preferences, {mode: 'enter'})
                                        dialog.accepted.connect(function() {
                                            Config.pinCode = dialog.pincode
                                            dialog.close()
                                        })
                                        dialog.rejected.connect(function() {
                                            checked = false
                                        })
                                        dialog.open()
                                    } else {
                                        focus = false
                                        Config.pinCode = ''
                                        // re-add binding, pincode still set if auth failed
                                        checked = Qt.binding(function () { return Config.pinCode })
                                    }
                                }

                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('PIN protect payments')
                            wrapMode: Text.Wrap
                        }
                    }

                    Pane {
                        background: Rectangle { color: Material.dialogColor }
                        padding: 0
                        visible: Config.pinCode != ''
                        FlatButton {
                            text: qsTr('Modify')
                            onClicked: {
                                var dialog = pinSetup.createObject(preferences, {
                                    mode: 'change',
                                    pincode: Config.pinCode
                                })
                                dialog.accepted.connect(function() {
                                    Config.pinCode = dialog.pincode
                                    dialog.close()
                                })
                                dialog.open()
                            }
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        spacing: 0
                        Switch {
                            id: syncLabels
                            onCheckedChanged: {
                                if (activeFocus)
                                    AppController.setPluginEnabled('labels', checked)
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Synchronize labels')
                            wrapMode: Text.Wrap
                        }
                    }

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('Wallet behavior')
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        spacing: 0
                        Switch {
                            id: spendUnconfirmed
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.spendUnconfirmed = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Spend unconfirmed')
                            wrapMode: Text.Wrap
                        }
                    }

                  
                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('Advanced')
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        spacing: 0
                        Switch {
                            id: enableDebugLogs
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.enableDebugLogs = checked
                            }
                            enabled: Config.canToggleDebugLogs
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Enable debug logs (for developers)')
                            wrapMode: Text.Wrap
                        }
                    }
                }

            }
        }

    }

    Component {
        id: pinSetup
        Pin {}
    }

    Component.onCompleted: {
        language.currentIndex = language.indexOfValue(Config.language)
        baseUnit.currentIndex = _baseunits.indexOf(Config.baseUnit)
        thousands.checked = Config.thousandsSeparator
        currencies.currentIndex = currencies.indexOfValue(Daemon.fx.fiatCurrency)
        historicRates.checked = Daemon.fx.historicRates
        rateSources.currentIndex = rateSources.indexOfValue(Daemon.fx.rateSource)
        fiatEnable.checked = Daemon.fx.enabled
        spendUnconfirmed.checked = Config.spendUnconfirmed
        useFallbackAddress.checked = Config.useFallbackAddress
        enableDebugLogs.checked = Config.enableDebugLogs
        useRecoverableChannels.checked = Config.useRecoverableChannels
        syncLabels.checked = AppController.isPluginEnabled('labels')
    }
}
