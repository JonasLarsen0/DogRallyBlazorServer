using System.ComponentModel.DataAnnotations;
namespace DogRallyBlazorServer.Models.DTOs
{
    //Linked to the database when creating or editing a track. 
    public class AddTrackForm
    {
        [Required]
        public DateTime Date { get; set; }

        [Required]
        public string PlaceName { get; set; }

        [Required] 
        public string CreatorName { get; set; }

        [Required] 
        public string JudgeName { get; set; }

        [Required] 
        public RallyClass RallyClass { get; set; }
        
        public string? FileName { get; set; }
    }
}
