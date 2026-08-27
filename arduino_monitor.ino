#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const byte SCREEN_WIDTH = 128;
const byte SCREEN_HEIGHT = 64;
const int8_t OLED_RESET = -1;
const byte OLED_ADDRESS = 0x3C;
const byte BUTTON_PIN = 2;
const byte GREEN_LED_PIN = 7;
const byte RED_LED_PIN = 8;
const byte BUZZER_PIN = 9;

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
volatile bool buttonPressed = false;
volatile unsigned long lastInterruptTime = 0;
const unsigned long DEBOUNCE_DELAY = 50; // 50ms debounce time
String alertPid;
bool alertActive = false;

void onButtonPressed() {
  unsigned long currentTime = millis();
  if (currentTime - lastInterruptTime > DEBOUNCE_DELAY) {
    buttonPressed = true;
    lastInterruptTime = currentTime;
  }
}

void showStatus(const String &firstLine, const String &secondLine) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  
  // Draw decorative frame
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.fillRect(0, 0, 128, 12, SSD1306_WHITE);
  
  // Inverted text for header
  display.setTextColor(SSD1306_BLACK);
  display.setCursor(2, 2);
  display.println("STATUS");
  
  // Reset text color
  display.setTextColor(SSD1306_WHITE);
  
  display.setCursor(2, 24);
  display.println(firstLine.substring(0, 20));
  display.setCursor(2, 40);
  display.println(secondLine.substring(0, 20));
  
  // Draw status indicator box
  display.drawRect(110, 54, 16, 8, SSD1306_WHITE);
  
  display.display();
}

void showAlert(const String &message) {
  int firstSeparator = message.indexOf('|');
  int secondSeparator = message.indexOf('|', firstSeparator + 1);
  int thirdSeparator = message.indexOf('|', secondSeparator + 1);
  if (firstSeparator < 0 || secondSeparator < 0 || thirdSeparator < 0) {
    return;
  }

  alertPid = message.substring(firstSeparator + 1, secondSeparator);
  String name = message.substring(secondSeparator + 1, thirdSeparator);
  
  // Create visual alert display
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  
  // Draw alert frame
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.fillRect(0, 0, 128, 12, SSD1306_WHITE);
  
  // Inverted text for header
  display.setTextColor(SSD1306_BLACK);
  display.setCursor(2, 2);
  display.println("!!! ALERT !!!");
  
  // Reset text color
  display.setTextColor(SSD1306_WHITE);
  
  display.setCursor(2, 20);
  display.println("FROZEN:");
  display.setCursor(2, 32);
  display.println(name.substring(0, 16));
  
  display.setCursor(2, 48);
  display.println("PID: " + alertPid);
  
  // Draw X mark
  display.drawLine(116, 52, 124, 60, SSD1306_WHITE);
  display.drawLine(124, 52, 116, 60, SSD1306_WHITE);
  
  display.display();
  
  digitalWrite(RED_LED_PIN, HIGH);
  digitalWrite(GREEN_LED_PIN, LOW);
  tone(BUZZER_PIN, 2200, 300);
  alertActive = true;
}

void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(GREEN_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), onButtonPressed, FALLING);
  Serial.begin(9600);

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    while (true) {
      digitalWrite(RED_LED_PIN, HIGH);
      delay(250);
      digitalWrite(RED_LED_PIN, LOW);
      delay(250);
    }
  }

  // Show initial status with visual design
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  
  // Draw frame
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.fillRect(0, 0, 128, 12, SSD1306_WHITE);
  
  // Inverted text for header
  display.setTextColor(SSD1306_BLACK);
  display.setCursor(2, 2);
  display.println("MONITOR");
  
  // Reset text color
  display.setTextColor(SSD1306_WHITE);
  
  display.setCursor(2, 24);
  display.println("System OK");
  display.setCursor(2, 40);
  display.println("Waiting...");
  
  // Draw checkmark
  display.drawLine(116, 52, 120, 58, SSD1306_WHITE);
  display.drawLine(120, 58, 126, 48, SSD1306_WHITE);
  
  display.display();
  digitalWrite(GREEN_LED_PIN, HIGH);
}

void loop() {
  if (Serial.available()) {
    String message = Serial.readStringUntil('\n');
    message.trim();
    if (message.startsWith("ALERT|")) {
      showAlert(message);
    }
  }

  if (buttonPressed && alertActive) {
    noInterrupts();
    buttonPressed = false;
    interrupts();
    Serial.print("KILL|");
    Serial.println(alertPid);
    
    // Show kill confirmation with visual design
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    
    // Draw frame
    display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
    display.fillRect(0, 0, 128, 12, SSD1306_WHITE);
    
    // Inverted text for header
    display.setTextColor(SSD1306_BLACK);
    display.setCursor(2, 2);
    display.println("KILL CMD");
    
    // Reset text color
    display.setTextColor(SSD1306_WHITE);
    
    display.setCursor(2, 24);
    display.println("Terminating");
    display.setCursor(2, 40);
    display.println("PID: " + alertPid);
    
    // Draw arrow
    display.drawLine(116, 52, 126, 56, SSD1306_WHITE);
    display.drawLine(126, 56, 116, 60, SSD1306_WHITE);
    
    display.display();
    
    digitalWrite(RED_LED_PIN, LOW);
    digitalWrite(GREEN_LED_PIN, HIGH);
    noTone(BUZZER_PIN);
    alertActive = false;
    delay(500); // Prevent accidental double-presses
  }
}
