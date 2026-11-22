#include <Arduino.h>
#include <string.h>

constexpr unsigned long BAUD_RATE = 115200;
constexpr int SERVO_PIN = 18;
constexpr int SERVO_CHANNEL = 0;
constexpr int CLOSED_DEG = 20;
constexpr int OPEN_DEG = 90;
constexpr unsigned long HOLD_MS = 1500;
char line[80];
size_t used = 0;
bool overflow = false;

bool knownIdentity(const char* identity) {
    return strlen(identity) == 3 && identity[0] == 'K' && identity[1] == '0'
           && identity[2] >= '1' && identity[2] <= '4';
}

void writeAngle(int degrees) {
    int usec = map(constrain(degrees, 0, 180), 0, 180, 500, 2400);
    uint32_t duty = (uint32_t)usec * 65535UL / 20000UL;
    ledcWrite(SERVO_CHANNEL, duty);
}

void pulseOpen() {
    writeAngle(OPEN_DEG);
    delay(HOLD_MS);
    writeAngle(CLOSED_DEG);
}

void handleLine(char* input) {
    if (strcmp(input, "PING") == 0) {
        Serial.println("PONG FACENEXUS LATCH 1");
        return;
    }

    if (strncmp(input, "CHECK ", 6) != 0) {
        Serial.println("ERROR BAD_COMMAND");
        return;
    }

    char* event = strtok(input + 6, " ");
    char* identity = strtok(nullptr, " ");
    char* decision = strtok(nullptr, " ");
    if (event == nullptr || identity == nullptr || decision == nullptr
            || strtok(nullptr, " ") != nullptr || strlen(event) > 16
            || strspn(event, "0123456789") != strlen(event)) {
        Serial.println("ERROR BAD_COMMAND");
        return;
    }

    bool known = knownIdentity(identity);
    bool granted = strcmp(decision, "GRANTED") == 0;
    bool denied = strcmp(decision, "DENIED") == 0;
    if (!(known || strcmp(identity, "UNKNOWN") == 0)
            || !(granted || denied) || (granted && !known)) {
        Serial.println("ERROR BAD_DECISION");
        return;
    }

    if (granted) {
        pulseOpen();
        Serial.printf("ACK %s %s %s ACTUATED\n", event, identity, decision);
        return;
    }
    Serial.printf("ACK %s %s %s CLOSED\n", event, identity, decision);
}

void setup() {
    ledcSetup(SERVO_CHANNEL, 50, 16);
    ledcAttachPin(SERVO_PIN, SERVO_CHANNEL);
    writeAngle(CLOSED_DEG);
    Serial.begin(BAUD_RATE);
    Serial.println("READY FACENEXUS LATCH 1");
}

void loop() {
    while (Serial.available()) {
        char byte = static_cast<char>(Serial.read());
        if (byte == '\n') {
            if (overflow) {
                Serial.println("ERROR LINE_TOO_LONG");
            } else {
                if (used > 0 && line[used - 1] == '\r') {
                    --used;
                }
                line[used] = '\0';
                handleLine(line);
            }
            used = 0;
            overflow = false;
        } else if (used < sizeof(line) - 1 && !overflow && byte != '\0') {
            line[used++] = byte;
        } else {
            overflow = true;
        }
    }
}
