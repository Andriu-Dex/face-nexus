#include <Arduino.h>
#include <string.h>

constexpr unsigned long BAUD_RATE = 115200;
char line[80];
size_t used = 0;
bool overflow = false;

bool knownIdentity(const char* identity) {
    return strlen(identity) == 3 && identity[0] == 'K' && identity[1] == '0'
           && identity[2] >= '1' && identity[2] <= '4';
}

void handleLine(char* input) {
    if (strcmp(input, "PING") == 0) {
        Serial.println("PONG FACENEXUS BENCH 1");
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

    // El banco confirma recepción. El firmware no configura ninguna salida física.
    Serial.printf("ACK %s %s %s SIMULATED\n", event, identity, decision);
}

void setup() {
    Serial.begin(BAUD_RATE);
    Serial.println("READY FACENEXUS BENCH 1");
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
