from typing import List

from requests import HTTPError
from rich import print
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline, AutoModelForQuestionAnswering


def load_qg(model: str, device: str):
    """
    Load Question Generation model from HuggingFace hub

    Args:
        model (str): model name to be loaded
        device (str): device info

    Returns:
        function: question generation function

    """
    try:
        tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(model, local_files_only=True).to(device)
    except (HTTPError, OSError):
        print("Input model is not supported by HuggingFace Hub")

    def generate_question(sentences: List[str], total_entities: List):
        """
        Generation question using context and entity information

        Args:
            sentences (List[str]): list of sentences
            total_entities (List): list of entities

        Returns:
            List[Dict] list of question and answer (entity) pairs

        """
        qa_pairs = list()

        for sentence, line_entities in zip(sentences, total_entities):
            for entity in line_entities:
                entity = entity["word"]

                template = f"answer: {entity}  context: {sentence} </s>"

                # TODO: batchify
                tokens = tokenizer(
                    template,
                    padding="max_length",
                    max_length=512,
                    truncation=True,
                    return_tensors="pt",
                ).to(device)

                outputs = model.generate(**tokens, max_length=64)

                question = tokenizer.decode(outputs[0])
                question = question.replace("</s>", "")
                question = question.replace("<pad> question: ", "")

                qa_pairs.append({
                    "question": question,
                    "answer": entity,
                })

        return qa_pairs

    return generate_question


def load_qa(model: str, device: str):
    """
    Load Question Answering model from HuggingFace hub

    Args:
        model (str): model name to be loaded
        device (str): device info

    Returns:
        function: question answering function

    """

    try:
        qa = pipeline(
            "question-answering",
            model=model,
            tokenizer=model,
            framework="pt",
            device=-1 if device == "cpu" else 0,
        )
    except (HTTPError, OSError):
        print("Input model is not supported by HuggingFace Hub")

    def answer_question(context: str, qa_pairs: List):
        """
        Answer question via Span Prediction

        Args:
            context (str): context to be encoded
            qa_pairs (List): Question & Answer pairs generated from Question Generation pipe

        """
        answers = list()
        for qa_pair in qa_pairs:
            pred = qa(
                question=qa_pair["question"],
                context=context,
                handle_impossible_answer=True,
            )["answer"]
            answers.append({
                "question": qa_pair["question"],
                "answer": qa_pair["answer"],
                "prediction": pred if pred != "" else "<unanswerable>"
            })
        return answers

    return answer_question
