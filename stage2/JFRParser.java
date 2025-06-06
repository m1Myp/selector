import jdk.jfr.consumer.EventStream;
import jdk.jfr.consumer.RecordedEvent;
import jdk.jfr.consumer.RecordedFrame;
import jdk.jfr.consumer.RecordedStackTrace;

import java.io.IOException;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.StringJoiner;

/**
 * JFRParser processes a .jfr file to extract method call counts (histogram).
 *
 * Input:
 * - A path to a .jfr file, provided as a command-line argument.
 *
 * Output:
 * - A histogram of method call counts, printed in the format:
 *   "method_name": call_count
 *   This is the frequency of method calls found in the provided .jfr file.
 */
public class JFRParser {

    /**
     * Main method to execute the JFR file parsing.
     * 
     * Input: 
     * - Path to the .jfr file (passed as a command-line argument).
     * 
     * Output:
     * - A JSON-like string of method call counts, where method names are the keys and call counts are the values.
     * 
     * @param args Command-line arguments containing the path to the .jfr file.
     * @throws IOException If there is an issue reading the file or processing the JFR data.
     */
    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            System.err.println("[ERROR] Usage: java JFRParser <path_to_jfr_file>");
            System.exit(1);
        }

        Path jfrPath = Path.of(args[0]);
        Map<String, Integer> histo = parseJFRFile(jfrPath);

        String jsonString = mapToJsonString(histo);

        System.out.println(jsonString);
    }

    /**
     * Parses a JFR file and builds a histogram of method call counts.
     * 
     * Input:
     * - A Path object pointing to a valid .jfr file.
     * 
     * Output:
     * - A map containing method names as keys and their call counts as values.
     * 
     * @param jfrPath Path to the .jfr file to parse.
     * @return A Map with method names as keys and call counts as values.
     * @throws IOException If there is an issue processing the file or events.
     */
    private static Map<String, Integer> parseJFRFile(Path jfrPath) throws IOException {
        Map<String, Integer> methodCounts = new HashMap<>();

        try (EventStream eventStream = EventStream.openFile(jfrPath)) {
            eventStream.onEvent("jdk.ExecutionSample", event -> processEvent(event, methodCounts));
            eventStream.start();
        }

        return methodCounts;
    }

    /**
     * Processes each JFR event to extract the method name and increment its call count.
     * 
     * Input:
     * - A RecordedEvent object representing the event to process.
     * - A Map to track the call counts of methods.
     * 
     * Output:
     * - Updates the Map with the method name as the key and the call count as the value.
     * 
     * @param event The JFR event to process.
     * @param methodCounts The Map of method names and their corresponding call counts.
     */
    private static void processEvent(RecordedEvent event, Map<String, Integer> methodCounts) {
        RecordedStackTrace stackTrace = event.getStackTrace();

        if (stackTrace != null && !stackTrace.getFrames().isEmpty()) {
            RecordedFrame topFrame = stackTrace.getFrames().get(0);

            String methodName = topFrame.getMethod().getType().getName() + "." + topFrame.getMethod().getName();

            methodCounts.merge(methodName, 1, Integer::sum);
        }
    }

    /**
     * Converts a map of method names and their corresponding call counts into a JSON-formatted string.
     * The resulting string represents a JSON object with method names as keys and call counts as values.
     * Example output: {"com.example.Foo.bar": 12, "com.example.Baz.qux": 8}
     *
     * @param map A map where keys are method names (as Strings) and values are their call counts (as Integers).
     * @return A JSON-formatted string representing the contents of the map.
     */
    private static String mapToJsonString(Map<String, Integer> map) {
        StringJoiner jsonJoiner = new StringJoiner(",", "{", "}");
        for (Map.Entry<String, Integer> entry : map.entrySet()) {
            jsonJoiner.add("\"" + escapeJson(entry.getKey()) + "\": " + entry.getValue());
        }
        return jsonJoiner.toString();
    }

    /**
     * Escapes characters in a string to make it JSON-compliant.
     * Specifically, it escapes double quotes and backslashes,
     * replacing " with \" and \ with \\ to ensure the string is valid in JSON output.
     *
     * @param value The input string to escape.
     * @return A JSON-safe version of the input string with special characters escaped.
     */
    private static String escapeJson(String value) {
        return value.replace("\"", "\\\"").replace("\\", "\\\\");
    }
}
