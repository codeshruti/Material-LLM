import random
import json
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key="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")

# Generate prompt based on user input
def generate_prompt(composition, property_value, target_property, modification_history, constraints):
    return f"""
    You are an expert in Material Physics. I have a material with a known band gap. The band gap is {property_value} eV.
    Material: {composition}

    Objective:
    Modify the material to achieve a target band gap of {target_property} eV.
    You can choose one of the following modification types:
      1. exchange: exchange two elements in the material
      2. substitute: substitute one element in the material with another
      3. remove: remove an element from the material
      4. add: add an element to the material

    Constraints: {constraints}

    Your response should be a Python dictionary in the following format:
    {{
        "Hypothesis": "$HYPOTHESIS",
        "Modification": ["$TYPE", "$ELEMENT_1", "$ELEMENT_2"]
    }}
    Give a hypothesis for the modification and specify the type and elements involved. Please provide your response strictly in JSON format, without any additional explanation or text outside the JSON.
    Modification History:
    {modification_history}
    """

# Apply material modification
def modify_material(composition, modification):
    mod_type, elem1, elem2 = modification
    if mod_type == "substitute":
        return composition.replace(elem1, elem2)
    elif mod_type == "add":
        return composition + f" + {elem1}"
    elif mod_type == "remove":
        return composition.replace(elem1, "")
    elif mod_type == "exchange":
        return composition.replace(elem1, elem2).replace(elem2, elem1)
    return composition

# Simulate property prediction 
def predict_property(composition):
    return round(random.uniform(0.5, 3.0), 2)

# LLMatDesign Workflow
def llmatdesign_workflow(starting_composition, starting_band_gap, target_band_gap, constraints, max_iterations=50):
    current_composition = starting_composition
    current_band_gap = starting_band_gap
    modification_history = []

    for iteration in range(max_iterations):
        prompt = generate_prompt(
            current_composition, current_band_gap, target_band_gap, modification_history, constraints
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.6
            )
            #st.write(f"Iteration {iteration + 1}: API response received")
            content = response.choices[0].message.content.strip()
            #st.write("Raw suggestion content:", content)
            
            # Attempt to parse the suggestion
            try:
                suggestion = json.loads(content)
            except json.JSONDecodeError as json_err:
                st.error(f"JSON Parsing Error: {json_err}")
                st.write("Response Content was not valid JSON. Please check the response:")
                st.code(content, language="json")
                return modification_history, "Error: Response content was not in JSON format."

            # Extract hypothesis and modification from the suggestion
            hypothesis = suggestion.get("Hypothesis", "No hypothesis provided")
            modification = suggestion.get("Modification", [])
            
            if not modification:
                raise ValueError("No valid modification suggested.")
        except Exception as e:
            st.error(f"Error during API call or response parsing: {str(e)}")
            return modification_history, f"Error: {str(e)}"


        # Apply the suggested modification
        current_composition = modify_material(current_composition, modification)
        new_band_gap = predict_property(current_composition)

        # Log modification
        modification_history.append({
            "Iteration": iteration + 1,
            "Composition": current_composition,
            "Hypothesis": hypothesis,
            "Modification": modification,
            "Band Gap": new_band_gap,
        })

        # Display the current state
        #st.write(f"Iteration {iteration + 1} Results:")
        #st.json(modification_history[-1])

        # Check if the target band gap is achieved
        if abs(new_band_gap - target_band_gap) / target_band_gap <= 0.1:
            return modification_history, f"Target achieved: {current_composition} with band gap {new_band_gap} eV."

        # Update the current band gap for the next iteration
        current_band_gap = new_band_gap

    return modification_history, "Target not achieved within the maximum iterations."

st.title("LLMatDesign Framework")
starting_composition = st.text_input("Starting Composition", "CdCu2GeS4")
starting_band_gap = st.number_input("Starting Band Gap (eV)", min_value=0.0, value=0.39, step=0.01)
target_band_gap = st.number_input("Target Band Gap (eV)", min_value=0.0, value=1.4, step=0.01)
constraints = st.text_area("Constraints (e.g., avoid certain elements)", "None")

if st.button("Run LLMatDesign Workflow"):
    with st.spinner("Running the workflow..."):
        history, result_message = llmatdesign_workflow(
            starting_composition, starting_band_gap, target_band_gap, constraints
        )
    st.success(result_message)
    st.subheader("Modification History")
    for step in history:
        st.json(step)