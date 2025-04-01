# Constants
NOVA_CANVAS_MODEL_ID = "amazon.nova-canvas-v1:0"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
DEFAULT_QUALITY = "standard"
DEFAULT_CFG_SCALE = 6.5
DEFAULT_NUMBER_OF_IMAGES = 1
DEFAULT_OUTPUT_DIR = "output"  # Default directory inside workspace_dir


# Nova Canvas Prompt Best Practices
PROMPT_INSTRUCTIONS = """
# Amazon Nova Canvas Prompting Best Practices

## General Guidelines

- Prompts must be no longer than 1024 characters. For very long prompts, place the least important details near the end.
- Do not use negation words like "no", "not", "without" in your prompt. The model doesn't understand negation and will result in the opposite of what you intend.
- Use negative prompts (via the `negative_prompt` parameter) to specify objects or characteristics to exclude from the image.
- Omit negation words from your negative prompts as well.

## Effective Prompt Structure

An effective prompt often includes short descriptions of:

1. The subject
2. The environment
3. (optional) The position or pose of the subject
4. (optional) Lighting description
5. (optional) Camera position/framing
6. (optional) The visual style or medium ("photo", "illustration", "painting", etc.)

## Refining Results

When the output is close to what you want but not perfect:

1. Use a consistent `seed` value and make small changes to your prompt or negative prompt.
2. Once the prompt is refined, generate more variations using the same prompt but different `seed` values.

## Examples

### Example 1: Stock Photo
**Prompt:** "realistic editorial photo of female teacher standing at a blackboard with a warm smile"
**Negative Prompt:** "crossed arms"

### Example 2: Story Illustration
**Prompt:** "whimsical and ethereal soft-shaded story illustration: A woman in a large hat stands at the ship's railing looking out across the ocean"
**Negative Prompt:** "clouds, waves"

### Example 3: Pre-visualization for TV/Film
**Prompt:** "drone view of a dark river winding through a stark Iceland landscape, cinematic quality"

### Example 4: Fashion/Editorial Content
**Prompt:** "A cool looking stylish man in an orange jacket, dark skin, wearing reflective glasses. Shot from slightly low angle, face and chest in view, aqua blue sleek building shapes in background."

## Using Negative Prompts

Negative prompts can be surprisingly useful. Use them to exclude objects or style characteristics that might otherwise naturally occur as a result of your main prompt.

For example, adding "waves, clouds" as a negative prompt to a ship scene will result in a cleaner, more minimal composition.
"""
