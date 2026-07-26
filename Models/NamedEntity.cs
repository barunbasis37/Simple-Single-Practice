namespace SimpleSinglePractice.Models;

public abstract class NamedEntity
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Description { get; set; }
}
