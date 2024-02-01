# sd-dynamic-prompts-parser

This is an unofficial Python parser for the [sd-dynamic-prompt](https://github.com/adieyal/sd-dynamic-prompts) extension's dynamic prompt syntax parsing. 

## Features

It supports the basics of sd-dynamic-prompt syntax:

* **Wildcards file**: Either load from `wildcards.yaml` or from txt files in the `wildcard` folder. The YAML file can be converted from txt files using:
  
  ```python
  # Load & update to wildcards.yaml
  from prompt_parser import load_wildcard
  data = load_wildcard()
  ```
  
  To use wildcard in the prompt, embedded it in a pair of double-underlines: `__cloth/dress-style__`.

* **Random choices syntax**:
  
  Examples for randomly choosing 1 item from 3. Items are separated by vertical line (`|`) and they can be either literal strings, wildcards, or nested random contents.
  ```
  {red|blue|green}
  {cyan|violet|__color__}
  {sharp|{one|two|three}|left bracket, right paren}
  ```
  
  - **Weights**: Optionally, weights can be assigned to items. In the process, these weights are normalized and then sent to numpy for weighted random choose.
    ```
    {0.5::red|2::blue|green}
    ```
    
    Weights should be positive float. If an item doesn't have an explicit weight, it will be set to 1.0.

  - **Numbers to Draw**: We can also optionally specify the number of items to draw. Use `$$` as the separator. Here, we randomly choose 2 items (without replacing items back):
    ```
    {2$$red|blue|green}
    ```

    Or, we can use number ranges to draw X number of items. Here, X can be either 1, 2, or 3:
    ```
    {1-3$$red|blue|green}
    ```
    
    Numbers to draw should be positive integers. 

  - **Separator**: The default separator for these items are `', '`, a comma with a space; therefore, the above example will possibly return `red, green` as a result. I preferred this separator, but it is different from the setting of the original extension. 

    The separator can also be specified by the user. In this example, we would like to use `; ` as the separator:
    ```
    {2$$; $$red|blue|green}
    ```

## Quick guide

Use the `parse_prompt` function after importing `prompt_parser.py` in your Python code. 

* Prepare your wildcard files in advance. The `load_wildcard` function will try to load the existing YAML first; if not found, it will load txt files in the wildcard folder and then save the data to YAML.
* If needed, open your `wildcard.yaml` file to check if your wildcard entry is registered.

An example:

```python
from prompt_parser import parse_prompt, load_wildcard

prompt = 'The quick __color__ cat jumps over the lazy {dog|fox} '
wildcards = load_wildcard()
result = parse_prompt(prompt, wildcards)
print(result)
```

Alternatively, you can run `python prompt_parser.py` to see another example that goes with the file.

## License

[MIT](./LICENSE)
